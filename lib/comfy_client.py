"""Shared ComfyUI API helpers and UI→API conversion."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any, TextIO


DEFAULT_SERVER = "127.0.0.1:8188"
WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMFYUI_INPUT_DIR = r"F:\ComfyUI_windows_portable\ComfyUI\input"
DEFAULT_TIMEOUT_SEC = 600
POLL_INTERVAL_SEC = 1.0

# Local portable default launcher (override with AGENT_COMFY_LAUNCH_BAT).
DEFAULT_LAUNCH_BAT = (
    r"F:\ComfyUI_windows_portable\run_nvidia_gpu_fast_fp16_accumulation.bat"
)
DEFAULT_READY_TIMEOUT_SEC = 180.0
DEFAULT_PROBE_TIMEOUT_SEC = 3.0
# After we spawn a launcher, skip re-spawn for this long even without a live lock.
DEFAULT_LAUNCH_COOLDOWN_SEC = 120.0

_AGENT_CACHE_DIR = os.path.join(WORKSPACE_ROOT, ".agent_cache")
_LAUNCH_LOCK_PATH = os.path.join(_AGENT_CACHE_DIR, "comfy_launch.lock")
_LAUNCH_STATE_PATH = os.path.join(_AGENT_CACHE_DIR, "comfy_launch_state.json")
_COMFY_LOG_HINT = r"F:\ComfyUI_windows_portable\ComfyUI\user\comfyui.log"

MODEL_MAPPING = {
    "real": "ZImageTurbo\\moodyRealMix_zitV6DPO.safetensors",
    "pro": "ZImageTurbo\\moodyProMix_zitV12DPO.safetensors",
    "wild": "ZImageTurbo\\moodyWildMixZIBZID_v01.safetensors",
}

# Process-local: servers confirmed up after ensure (avoid redundant full ensure chatter).
_ready_servers: set[str] = set()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)


def write_meta(path: str, data: dict[str, Any]) -> None:
    ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def resolve_meta_out(output_filename: str | None, meta_out: str | None) -> str | None:
    if meta_out:
        return meta_out
    if output_filename:
        base, _ = os.path.splitext(output_filename)
        return base + ".json"
    return None


# ---------------------------------------------------------------------------
# ComfyUI process ensure (auto-start if local server is down)
# ---------------------------------------------------------------------------


def _env_flag(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    return str(raw).strip().lower() not in ("0", "false", "no", "off", "disable", "disabled")


def autostart_enabled() -> bool:
    """AGENT_COMFY_AUTOSTART default on; set 0/false/off to fail-fast when down."""
    return _env_flag("AGENT_COMFY_AUTOSTART", default=True)


def resolve_launch_bat() -> str:
    override = (os.environ.get("AGENT_COMFY_LAUNCH_BAT") or "").strip()
    if override:
        return os.path.abspath(override)
    return DEFAULT_LAUNCH_BAT


def resolve_ready_timeout_sec(explicit: float | None = None) -> float:
    if explicit is not None:
        return float(explicit)
    raw = (os.environ.get("AGENT_COMFY_READY_TIMEOUT_SEC") or "").strip()
    if raw:
        try:
            return max(15.0, float(raw))
        except ValueError:
            pass
    return DEFAULT_READY_TIMEOUT_SEC


def is_comfy_reachable(
    server_address: str = DEFAULT_SERVER,
    *,
    timeout: float = DEFAULT_PROBE_TIMEOUT_SEC,
) -> bool:
    """Cheap probe — does NOT auto-start. Prefer /system_stats then /queue."""
    for path in ("/system_stats", "/queue"):
        try:
            _http_json(server_address, path, timeout=timeout)
            return True
        except Exception:
            continue
    return False


def _pid_alive(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    if sys.platform == "win32":
        # os.kill(pid, 0) is not reliable on all Windows Python builds; use OpenProcess.
        try:
            import ctypes

            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = ctypes.windll.kernel32.OpenProcess(
                PROCESS_QUERY_LIMITED_INFORMATION, False, int(pid)
            )
            if handle:
                ctypes.windll.kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:
            return False
    try:
        os.kill(int(pid), 0)
        return True
    except OSError:
        return False


def _load_launch_state() -> dict[str, Any] | None:
    try:
        if not os.path.isfile(_LAUNCH_STATE_PATH):
            return None
        with open(_LAUNCH_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _write_launch_state(data: dict[str, Any]) -> None:
    ensure_parent_dir(_LAUNCH_STATE_PATH)
    with open(_LAUNCH_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _clear_launch_state() -> None:
    try:
        if os.path.isfile(_LAUNCH_STATE_PATH):
            os.remove(_LAUNCH_STATE_PATH)
    except OSError:
        pass


def _recent_launch_in_progress(
    server_address: str,
    *,
    cooldown_sec: float = DEFAULT_LAUNCH_COOLDOWN_SEC,
) -> dict[str, Any] | None:
    """Return launch state only if a spawn is *likely still booting*.

    Important: do **not** block re-spawn for the full ready-timeout when the
    launcher PID is already dead and the API is still down — that made agents
    wait forever after a failed/killed start (state age < 180s → never re-run bat).
    """
    state = _load_launch_state()
    if not state:
        return None
    state_server = str(state.get("server") or DEFAULT_SERVER)
    if state_server != server_address:
        return None
    try:
        started = float(state.get("started_ts") or 0)
    except (TypeError, ValueError):
        started = 0.0
    age = time.time() - started if started else 1e9
    if age > cooldown_sec:
        return None
    pid = state.get("pid")
    try:
        pid_i = int(pid) if pid is not None else None
    except (TypeError, ValueError):
        pid_i = None

    # Short grace: cmd/start returns quickly; grandchild may still be starting.
    boot_grace_sec = min(45.0, float(cooldown_sec))
    if age <= boot_grace_sec:
        return state
    # After grace: only block if launcher process still alive.
    if pid_i is not None and _pid_alive(pid_i):
        return state
    # Stale state (API still down, launcher gone) → allow re-spawn.
    return None


class _LaunchLock:
    """Exclusive inter-process lock so only one agent spawns the bat."""

    def __init__(self, path: str = _LAUNCH_LOCK_PATH) -> None:
        self.path = path
        self._fh: TextIO | None = None
        self.acquired = False

    def try_acquire(self, timeout_sec: float = 15.0, poll: float = 0.2) -> bool:
        ensure_parent_dir(self.path)
        deadline = time.time() + timeout_sec
        while time.time() < deadline:
            try:
                fh = open(self.path, "a+", encoding="utf-8")
                if sys.platform == "win32":
                    import msvcrt

                    fh.seek(0)
                    try:
                        msvcrt.locking(fh.fileno(), msvcrt.LK_NBLCK, 1)
                    except OSError:
                        fh.close()
                        time.sleep(poll)
                        continue
                else:
                    import fcntl

                    try:
                        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except OSError:
                        fh.close()
                        time.sleep(poll)
                        continue
                self._fh = fh
                self.acquired = True
                fh.seek(0)
                fh.truncate()
                fh.write(f"pid={os.getpid()} ts={time.time()}\n")
                fh.flush()
                return True
            except OSError:
                time.sleep(poll)
        return False

    def release(self) -> None:
        if not self._fh:
            return
        try:
            if sys.platform == "win32":
                import msvcrt

                try:
                    self._fh.seek(0)
                    msvcrt.locking(self._fh.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
            else:
                import fcntl

                try:
                    fcntl.flock(self._fh.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass
        finally:
            try:
                self._fh.close()
            except OSError:
                pass
            self._fh = None
            self.acquired = False


def _launch_comfy_process(bat_path: str) -> int:
    """Start Comfy exactly like the portable bat — no start/startfile wrappers.

    Default bat (``run_nvidia_gpu_fast_fp16_accumulation.bat``) is literally:

        .\\python_embeded\\python.exe -s ComfyUI\\main.py ^
            --windows-standalone-build --fast fp16_accumulation --disable-smart-memory

    We run that same command with cwd = portable root (the bat's folder).
    """
    bat_path = os.path.abspath(bat_path)
    if not os.path.isfile(bat_path):
        raise FileNotFoundError(
            f"ComfyUI launch script not found: {bat_path} "
            f"(set AGENT_COMFY_LAUNCH_BAT to override)"
        )
    cwd = os.path.dirname(bat_path) or os.getcwd()

    # Same command line as the bat (absolute paths so cwd is unambiguous).
    py = os.path.join(cwd, "python_embeded", "python.exe")
    main_py = os.path.join(cwd, "ComfyUI", "main.py")
    if os.path.isfile(py) and os.path.isfile(main_py):
        args = [
            py,
            "-s",
            main_py,
            "--windows-standalone-build",
            "--fast",
            "fp16_accumulation",
            "--disable-smart-memory",
        ]
    else:
        # Unknown bat layout: still just "run the bat from its directory".
        args = ["cmd.exe", "/c", bat_path] if sys.platform == "win32" else [bat_path]

    if sys.platform == "win32":
        # New console window; do not pass stdin/stdout/stderr (avoids broken agent pipes).
        flags = int(getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010))
        proc = subprocess.Popen(
            args,
            cwd=cwd,
            creationflags=flags,
        )
        return int(proc.pid)

    proc = subprocess.Popen(
        args,
        cwd=cwd,
        start_new_session=True,
    )
    return int(proc.pid)


def wait_for_comfy_ready(
    server_address: str = DEFAULT_SERVER,
    *,
    timeout_sec: float | None = None,
    poll_interval: float = 1.5,
    log: bool = True,
) -> bool:
    """Poll until API answers or timeout. Returns True if ready."""
    timeout = resolve_ready_timeout_sec(timeout_sec)
    deadline = time.time() + timeout
    started = time.time()
    last_report = 0.0
    while time.time() < deadline:
        if is_comfy_reachable(server_address, timeout=DEFAULT_PROBE_TIMEOUT_SEC):
            if log:
                elapsed = time.time() - started
                print(
                    f"[comfy_ensure] ready at {server_address} after {elapsed:.1f}s",
                    file=sys.stderr,
                    flush=True,
                )
            return True
        now = time.time()
        if log and now - last_report >= 10.0:
            elapsed = now - started
            print(
                f"[comfy_ensure] waiting for ComfyUI at {server_address} "
                f"({elapsed:.0f}/{timeout:.0f}s)…",
                file=sys.stderr,
                flush=True,
            )
            last_report = now
        time.sleep(poll_interval)
    return False


def ensure_comfy_running(
    server_address: str = DEFAULT_SERVER,
    *,
    timeout_sec: float | None = None,
    force: bool = False,
    log: bool = True,
) -> dict[str, Any]:
    """Ensure ComfyUI HTTP API is up; auto-start local portable bat if needed.

    Duplicate-launch defenses:
      1) Probe /system_stats (or /queue) first — never spawn if already up.
      2) Inter-process lock (`.agent_cache/comfy_launch.lock`) for spawn critical section.
      3) Launch-state cooldown (`.agent_cache/comfy_launch_state.json`) so concurrent
         agents wait instead of starting a second console while the first is booting.

    Env:
      AGENT_COMFY_AUTOSTART=0          — disable auto-start (fail if down)
      AGENT_COMFY_LAUNCH_BAT=path.bat  — override launcher
      AGENT_COMFY_READY_TIMEOUT_SEC=N  — wait budget (default 180)
    """
    server_address = (server_address or DEFAULT_SERVER).strip()
    result: dict[str, Any] = {
        "ok": False,
        "server": server_address,
        "action": "none",
        "autostart": autostart_enabled(),
        "launch_bat": resolve_launch_bat(),
        "pid": None,
        "waited_sec": 0.0,
    }

    t0 = time.time()
    if not force and server_address in _ready_servers:
        if is_comfy_reachable(server_address):
            result["ok"] = True
            result["action"] = "already_running"
            result["waited_sec"] = time.time() - t0
            return result
        _ready_servers.discard(server_address)

    if is_comfy_reachable(server_address):
        _ready_servers.add(server_address)
        _clear_launch_state()
        result["ok"] = True
        result["action"] = "already_running"
        result["waited_sec"] = time.time() - t0
        return result

    if not autostart_enabled():
        raise ConnectionError(
            f"ComfyUI unreachable at {server_address} "
            f"(AGENT_COMFY_AUTOSTART=0). Start it manually or enable autostart. "
            f"Default launcher: {resolve_launch_bat()}"
        )

    bat = resolve_launch_bat()
    if not os.path.isfile(bat):
        raise FileNotFoundError(
            f"ComfyUI unreachable at {server_address} and launch script missing: {bat}. "
            f"Set AGENT_COMFY_LAUNCH_BAT or start ComfyUI manually."
        )

    ready_timeout = resolve_ready_timeout_sec(timeout_sec)
    launched_here = False
    launch_pid: int | None = None
    lock = _LaunchLock()
    got_lock = lock.try_acquire(timeout_sec=min(20.0, ready_timeout))

    try:
        # Another process may have finished booting while we waited for the lock.
        if is_comfy_reachable(server_address):
            _ready_servers.add(server_address)
            _clear_launch_state()
            result["ok"] = True
            result["action"] = "already_running"
            result["waited_sec"] = time.time() - t0
            return result

        if force:
            _clear_launch_state()

        recent = _recent_launch_in_progress(
            server_address, cooldown_sec=DEFAULT_LAUNCH_COOLDOWN_SEC
        )
        if recent and not force:
            if log:
                print(
                    f"[comfy_ensure] launch already in progress "
                    f"(pid={recent.get('pid')}, age≈{time.time() - float(recent.get('started_ts') or t0):.0f}s); "
                    f"waiting for {server_address}",
                    file=sys.stderr,
                    flush=True,
                )
            result["action"] = "wait_existing_launch"
            result["pid"] = recent.get("pid")
        elif got_lock:
            # Double-check under lock before spawn.
            if is_comfy_reachable(server_address):
                _ready_servers.add(server_address)
                _clear_launch_state()
                result["ok"] = True
                result["action"] = "already_running"
                result["waited_sec"] = time.time() - t0
                return result
            recent2 = _recent_launch_in_progress(
                server_address,
                cooldown_sec=DEFAULT_LAUNCH_COOLDOWN_SEC,
            )
            if recent2 and not force:
                result["action"] = "wait_existing_launch"
                result["pid"] = recent2.get("pid")
                if log:
                    print(
                        f"[comfy_ensure] concurrent launch state found; not re-spawning "
                        f"(pid={recent2.get('pid')})",
                        file=sys.stderr,
                        flush=True,
                    )
            else:
                if log:
                    print(
                        f"[comfy_ensure] ComfyUI down at {server_address}; "
                        f"starting: {bat}",
                        file=sys.stderr,
                        flush=True,
                    )
                launch_pid = _launch_comfy_process(bat)
                launched_here = True
                state = {
                    "server": server_address,
                    "bat": bat,
                    "pid": launch_pid,
                    "launcher_pid": os.getpid(),
                    "started_ts": time.time(),
                    "started_at": utc_now_iso(),
                }
                _write_launch_state(state)
                result["action"] = "launched"
                result["pid"] = launch_pid
                if log:
                    print(
                        f"[comfy_ensure] spawned launcher pid={launch_pid}; "
                        f"waiting up to {ready_timeout:.0f}s for API…",
                        file=sys.stderr,
                        flush=True,
                    )
        else:
            # Could not get lock — another agent is in the critical section; wait only.
            result["action"] = "wait_lock_holder"
            if log:
                print(
                    f"[comfy_ensure] launch lock busy; waiting for {server_address}…",
                    file=sys.stderr,
                    flush=True,
                )
    finally:
        lock.release()

    # Everyone (launcher or waiter) polls until ready.
    if wait_for_comfy_ready(
        server_address, timeout_sec=ready_timeout, log=log
    ):
        _ready_servers.add(server_address)
        _clear_launch_state()
        result["ok"] = True
        if result["action"] == "none":
            result["action"] = "became_ready"
        result["waited_sec"] = time.time() - t0
        return result

    hint = (
        f"ComfyUI did not become ready at {server_address} within {ready_timeout:.0f}s. "
        f"action={result['action']} launch_bat={bat} pid={result.get('pid')}. "
        f"Check GPU/driver and log: {_COMFY_LOG_HINT}. "
        f"If a console window is open, inspect errors there. "
        f"Retry or set AGENT_COMFY_AUTOSTART=0 and start manually."
    )
    raise TimeoutError(hint)


def convert_ui_to_api(ui_data: dict) -> dict:
    """Convert ComfyUI UI workflow JSON to API prompt format."""
    api_data = {}
    links = {l[0]: l for l in ui_data.get("links", [])}

    for node in ui_data.get("nodes", []):
        node_id = str(node["id"])
        class_type = node["type"]
        inputs: dict[str, Any] = {}

        for inp in node.get("inputs", []):
            name = inp["name"]
            link_id = inp.get("link")
            if link_id is not None and link_id in links:
                link = links[link_id]
                origin_node_id = str(link[1])
                origin_output_index = link[2]
                inputs[name] = [origin_node_id, origin_output_index]

        widgets_values = node.get("widgets_values", []) or []

        if class_type == "CLIPLoader":
            if len(widgets_values) >= 3:
                inputs["clip_name"] = widgets_values[0]
                inputs["type"] = widgets_values[1]
                inputs["device"] = widgets_values[2]
        elif class_type == "VAELoader":
            if len(widgets_values) >= 1:
                inputs["vae_name"] = widgets_values[0]
        elif class_type == "UNETLoader":
            if len(widgets_values) >= 2:
                inputs["unet_name"] = widgets_values[0]
                inputs["weight_dtype"] = widgets_values[1]
        elif class_type == "ModelSamplingAuraFlow":
            if len(widgets_values) >= 1:
                inputs["shift"] = widgets_values[0]
        elif class_type == "KSampler":
            if len(widgets_values) >= 7:
                inputs["seed"] = widgets_values[0]
                inputs["steps"] = widgets_values[2]
                inputs["cfg"] = widgets_values[3]
                inputs["sampler_name"] = widgets_values[4]
                inputs["scheduler"] = widgets_values[5]
                inputs["denoise"] = widgets_values[6]
        elif class_type in ("EmptySD3LatentImage", "EmptyLatentImage"):
            if len(widgets_values) >= 3:
                inputs["width"] = widgets_values[0]
                inputs["height"] = widgets_values[1]
                inputs["batch_size"] = widgets_values[2]
        elif class_type == "SaveImage":
            if len(widgets_values) >= 1:
                inputs["filename_prefix"] = widgets_values[0]
        elif class_type == "Prompt (LoraManager)":
            if len(widgets_values) >= 2:
                inputs["text"] = widgets_values[1]
        elif class_type == "Save Image (LoraManager)":
            if len(widgets_values) >= 2:
                inputs["filename_prefix"] = widgets_values[0]
                inputs["file_format"] = widgets_values[1]
        elif class_type == "Lora Loader (LoraManager)":
            if len(widgets_values) >= 3:
                inputs["text"] = widgets_values[1]
        elif class_type == "TriggerWord Toggle (LoraManager)":
            if len(widgets_values) >= 3:
                inputs["group_mode"] = widgets_values[0]
                inputs["default_active"] = widgets_values[1]
                inputs["allow_strength_adjustment"] = widgets_values[2]
        elif class_type == "CLIPTextEncode":
            if len(widgets_values) >= 1:
                inputs["text"] = widgets_values[0]
        elif class_type == "LoadImage":
            if len(widgets_values) >= 1:
                inputs["image"] = widgets_values[0]
                inputs["upload"] = "image"
        elif class_type == "VAEEncode":
            pass
        elif class_type == "ControlNetLoader":
            if len(widgets_values) >= 1:
                inputs["control_net_name"] = widgets_values[0]
        elif class_type == "FL_ZImageControlNetPatch":
            if len(widgets_values) >= 2:
                inputs["name"] = widgets_values[0]
                inputs["auto_config"] = widgets_values[1]
        elif class_type == "ZImageFunControlnet":
            if len(widgets_values) >= 1:
                inputs["strength"] = widgets_values[0]

        api_data[node_id] = {
            "inputs": inputs,
            "class_type": class_type,
        }
    return api_data


def load_workflow(workflow_path: str) -> dict:
    with open(workflow_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _http_json(
    server_address: str,
    path: str,
    *,
    method: str = "GET",
    body: dict | None = None,
    timeout: float = 30,
) -> Any:
    """GET/POST JSON helper for Comfy API. path like '/system_stats'."""
    url = f"http://{server_address}{path}"
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            if not raw:
                return {}
            return json.loads(raw.decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_body = ""
        try:
            err_body = e.read().decode("utf-8", errors="replace")[:2000]
        except Exception:
            pass
        raise ConnectionError(
            f"ComfyUI HTTP {e.code} at {server_address}{path}: {e.reason}. {err_body}"
        ) from e
    except urllib.error.URLError as e:
        raise ConnectionError(f"ComfyUI unreachable at {server_address}: {e}") from e


def get_system_stats(
    server_address: str = DEFAULT_SERVER,
    *,
    ensure: bool = True,
) -> dict[str, Any]:
    if ensure:
        ensure_comfy_running(server_address)
    return _http_json(server_address, "/system_stats", timeout=15)


def get_queue(
    server_address: str = DEFAULT_SERVER,
    *,
    ensure: bool = True,
) -> dict[str, Any]:
    if ensure:
        ensure_comfy_running(server_address)
    return _http_json(server_address, "/queue", timeout=15)


def interrupt_comfy(server_address: str = DEFAULT_SERVER) -> dict[str, Any]:
    """POST /interrupt — stop current execution if any.

    Does not auto-start Comfy (no-op if down).
    """
    try:
        return _http_json(server_address, "/interrupt", method="POST", body={}, timeout=30)
    except ConnectionError:
        # Some builds accept empty POST without JSON body
        req = urllib.request.Request(
            f"http://{server_address}/interrupt", data=b"{}", method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else {}


def free_comfy_memory(
    server_address: str = DEFAULT_SERVER,
    *,
    unload_models: bool = True,
    free_memory: bool = True,
    timeout: float = 120,
    ensure: bool = True,
) -> dict[str, Any]:
    """POST /free — unload models and/or free cached tensors.

    Only call when the execution queue is idle; mid-run free is often a no-op.
    """
    if ensure:
        ensure_comfy_running(server_address)
    return _http_json(
        server_address,
        "/free",
        method="POST",
        body={"unload_models": bool(unload_models), "free_memory": bool(free_memory)},
        timeout=timeout,
    )


def memory_snapshot(server_address: str = DEFAULT_SERVER) -> dict[str, Any]:
    """Normalize system_stats into GB/MB fields for guards and logs."""
    stats = get_system_stats(server_address)
    system = stats.get("system") or {}
    devices = stats.get("devices") or []
    dev = devices[0] if devices else {}
    ram_total = float(system.get("ram_total") or 0)
    ram_free = float(system.get("ram_free") or 0)
    vram_total = float(dev.get("vram_total") or 0)
    vram_free = float(dev.get("vram_free") or 0)
    torch_free = float(dev.get("torch_vram_free") or 0)
    return {
        "ram_total_gb": ram_total / (1024**3) if ram_total else 0.0,
        "ram_free_gb": ram_free / (1024**3) if ram_free else 0.0,
        "vram_total_mb": vram_total / (1024**2) if vram_total else 0.0,
        "vram_free_mb": vram_free / (1024**2) if vram_free else 0.0,
        "torch_vram_free_mb": torch_free / (1024**2) if torch_free else 0.0,
        "device_name": dev.get("name"),
        "argv": system.get("argv"),
        "raw": stats,
    }


def queue_prompt(server_address: str, api_prompt: dict) -> str:
    """Submit workflow; auto-starts local ComfyUI if needed (see ensure_comfy_running)."""
    ensure_comfy_running(server_address)
    payload = json.dumps({"prompt": api_prompt}).encode("utf-8")

    def _post() -> str:
        req = urllib.request.Request(
            f"http://{server_address}/prompt",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["prompt_id"]

    try:
        return _post()
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:2000]
        except Exception:
            pass
        raise ConnectionError(
            f"ComfyUI HTTP {e.code} at {server_address}: {e.reason}. {body}"
        ) from e
    except urllib.error.URLError as e:
        # One recovery attempt if the process died between ensure and POST.
        _ready_servers.discard(server_address)
        try:
            ensure_comfy_running(server_address, force=True)
            return _post()
        except Exception:
            pass
        raise ConnectionError(f"ComfyUI unreachable at {server_address}: {e}") from e


def history_execution_error(history_entry: dict) -> str | None:
    """Return a short error string if history entry is a failed execution."""
    status = history_entry.get("status") or {}
    messages = status.get("messages") or []
    for item in messages:
        if not isinstance(item, (list, tuple)) or not item:
            continue
        if item[0] != "execution_error":
            continue
        payload = item[1] if len(item) > 1 and isinstance(item[1], dict) else {}
        node = payload.get("node_type") or payload.get("node_id") or "?"
        msg = (payload.get("exception_message") or "").strip() or payload.get(
            "exception_type"
        ) or "execution_error"
        # Keep one line for agent logs
        msg = " ".join(str(msg).split())
        if len(msg) > 400:
            msg = msg[:400] + "…"
        return f"node={node}: {msg}"
    if status.get("status_str") == "error":
        return status.get("status_str") or "error"
    return None


def wait_for_history(
    server_address: str,
    prompt_id: str,
    timeout_sec: float = DEFAULT_TIMEOUT_SEC,
    poll_interval: float = POLL_INTERVAL_SEC,
) -> dict:
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                f"http://{server_address}/history/{prompt_id}", timeout=30
            ) as response:
                history = json.loads(response.read().decode("utf-8"))
                if prompt_id in history:
                    entry = history[prompt_id]
                    err = history_execution_error(entry)
                    if err:
                        raise RuntimeError(
                            f"ComfyUI execution failed (prompt_id={prompt_id}): {err}"
                        )
                    return entry
        except RuntimeError:
            raise
        except Exception:
            pass
        time.sleep(poll_interval)
    raise TimeoutError(f"ComfyUI timed out after {timeout_sec}s (prompt_id={prompt_id})")


def extract_first_image(history_entry: dict) -> tuple[str, str, str]:
    err = history_execution_error(history_entry)
    if err:
        raise FileNotFoundError(f"Output image missing (execution failed): {err}")
    outputs = history_entry.get("outputs", {})
    for _node_id, node_output in outputs.items():
        if "images" in node_output:
            for img in node_output["images"]:
                return (
                    img["filename"],
                    img.get("subfolder", ""),
                    img.get("type", "output"),
                )
    raise FileNotFoundError("Output image not found in ComfyUI history")


def extract_first_audio(history_entry: dict) -> tuple[str, str, str]:
    """Return (filename, subfolder, type) for first audio artifact in history."""
    outputs = history_entry.get("outputs", {})
    for _node_id, node_output in outputs.items():
        for key in ("audio", "audios"):
            if key not in node_output:
                continue
            items = node_output[key]
            if not isinstance(items, list):
                items = [items]
            for item in items:
                if isinstance(item, dict) and item.get("filename"):
                    return (
                        item["filename"],
                        item.get("subfolder", "") or "",
                        item.get("type", "output") or "output",
                    )
        # Some nodes put a single dict
        if isinstance(node_output.get("gifs"), list):
            pass
    raise FileNotFoundError("Output audio not found in ComfyUI history")


def download_image(
    server_address: str,
    filename: str,
    subfolder: str,
    image_type: str,
    dest_path: str,
) -> str:
    ensure_parent_dir(dest_path)
    view_url = (
        f"http://{server_address}/view?"
        f"filename={urllib.parse.quote(filename)}"
        f"&subfolder={urllib.parse.quote(subfolder)}"
        f"&type={image_type}"
    )
    urllib.request.urlretrieve(view_url, dest_path)
    return dest_path


def download_audio(
    server_address: str,
    filename: str,
    subfolder: str,
    media_type: str,
    dest_path: str,
) -> str:
    """Same /view endpoint as images; works for SaveAudio outputs."""
    return download_image(server_address, filename, subfolder, media_type, dest_path)


def fail_result(**extra) -> dict:
    result = {"ok": False, "output_path": None, "seed": None, "prompt_id": None, "meta_path": None}
    result.update(extra)
    return result


def ok_result(**extra) -> dict:
    result = {"ok": True}
    result.update(extra)
    return result
