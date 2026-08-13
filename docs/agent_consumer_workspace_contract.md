# 에이전트 소비자 계약 — 도구 상자 vs 내 프로젝트

- **대상**: 이 레포(`agent_custom`) CLI를 **도구로 호출**하는 에이전트
- **이 레포**: ComfyUI **미디어 도구 모음** ([tool_catalog.md](tool_catalog.md)) — 프로젝트 공정 전체가 아님
- **문제**: 결과가 도구 레포 기본 경로에만 남고 프로젝트로 안 가져오면 이후 작업이 끊김
- **관련**: [AGENTS.md](../AGENTS.md) · [agent_rules.md](../agent_rules.md)

---

## 1. 한 줄 규칙

> **도구 레포 = 공구함.** 코드·워크플로·템플릿만.  
> **프로젝트 폴더 = 작업대.** 모든 생성 미디어는 여기.  
> 공구함에 mp4/png/wav/zip을 쌓지 않는다.

---

## 2. 경로 SSOT

| 구분 | 경로 | 의미 |
|------|------|------|
| 도구 코드 | `scripts/`, `lib/`, `workflows/agent/` | 실행만 |
| 스캐폴드 | `stories/_template`, `characters/_template`, `locations/_template`, schemas | 빈 뼈대·프리셋. 작업물이 아님 |
| **에이전트 작업대** | **호출 측 프로젝트** (`-o` / `AGENT_WORKSPACE`) | 키프레임·클립·시트·납품 **유일한 저장소** |

CLI는 이 레포를 cwd로 실행해도 된다. **출력 경로는 항상 프로젝트 쪽.**  
`stories/<ep>/` · `dumps/` · `characters/<id>/` 에 쓰던 예전 기본값은 **스테이징이 아니라 금지**로 본다.

---

## 3. 필수 행동 (Consumer Agent)

### 3.1 작업 시작 전

1. **내 작업대 경로**를 정한다: `AGENT_WORKSPACE` 또는 브리프의 `project_dir`.  
2. **에피소드 id**를 정한다 (영문 소문자·숫자·`_`).  
3. ComfyUI `127.0.0.1:8188` — **CLI가 자동 ensure** 한다 (`lib/comfy_client.ensure_comfy_running`).  
   - 꺼져 있으면 기본 런처 bat으로 기동 후 ready 대기 (중복 기동 방지 포함).  
   - 사전 점검만: `python scripts/comfy_ensure.py` 또는 `--status`.  
   - 끄기: `AGENT_COMFY_AUTOSTART=0` (fail-fast).  
4. 이 레포 루트에서 CLI 실행:
   ```bash
   cd F:/ComfyUI_workflows/agent_custom
   python scripts/...
   ```

### 3.2 생성 (의무)

처음부터 **작업대 절대 경로**를 지정한다.

```bash
python scripts/generate_i2v.py -i ".../S01.png" -o "D:/projects/client_film/clips/S01.mp4"
python scripts/generate_krea.py --prompt "..." -o "D:/projects/client_film/stills/hero.png"
```

에피소드 레일을 쓸 때도 `story_init` / assemble 출력을 **프로젝트 아래**에 둔다.  
도구 레포 `stories/`에 에피를 만들고 export로 옮기는 흐름은 쓰지 않는다.

### 3.3 금지

- `-o` 없이 기본 `dumps/` · `stories/` 에 쌓고 “생성 끝”  
- 산출물 경로를 읽지 않고 완료 보고  
- 이 레포에 캐릭터 시트·에피소드 mp4·유튜브 원본을 보관

### 3.4 완료 보고 형식 (에이전트 → 사람)

```text
tool_repo: F:/ComfyUI_workflows/agent_custom
episode: stories/<ep>/
workspace_copy: <AGENT_WORKSPACE>/...
artifacts:
  - final: ...
  - keyframes: ...
lip_status: pending|approved (SI2V)
```

**workspace_copy 가 없으면 미완료**로 간주한다.

---

## 4. 도구 쪽 출력 계약

| 이벤트 | 에이전트가 볼 것 |
|--------|------------------|
| pipeline 종료 | stdout `=== AGENT_RESULT ===` + `meta/agent_pipeline_result.json` |
| 개별 generate | stdout `OK path=...` / `output=...` |
| smoke | `meta/agent_smoke_result.json` |

모든 성공 경로에 **절대 경로**가 찍히도록 하는 것이 목표다.  
경로를 봤으면 **반드시 작업대로 옮기거나 링크**한다.

---

## 5. 환경 변수 (선택)

| 변수 | 의미 |
|------|------|
| `AGENT_WORKSPACE` | 기본 export 목적지 루트 — 설정 시 `episode_i2v`/`s2v`/`tts` **자동 export (P0-3)** |
| `AGENT_EXPORT_WORKSPACE` | `1` 강제 on / `0` 강제 off (미설정 시 WORKSPACE 유무로 판단) |
| `--export-workspace` / `--export-dest` / `--no-export-workspace` | CLI 오버라이드 |
| `AGENT_CUSTOM_ROOT` | 도구 레포 루트 (드물게 필요) |
| `AGENT_COMFY_AUTOSTART` | 기본 on. `0`/`false`/`off` 이면 Comfy 다운 시 기동하지 않고 실패 |
| `AGENT_COMFY_LAUNCH_BAT` | Comfy 기동 bat (기본 `F:\ComfyUI_windows_portable\run_nvidia_gpu.bat`) |
| `AGENT_COMFY_READY_TIMEOUT_SEC` | 기동 후 API ready 대기 초 (기본 180) |

```bash
set AGENT_WORKSPACE=D:\projects\client_film
python scripts/export_episode_to_workspace.py -e my_ep
# → %AGENT_WORKSPACE%/episodes/my_ep/ 또는 --dest
```

---

## 6. 공장 스테이징 vs 정리 (lifecycle)

공장은 **일시 스테이징을 허용**한다. 금지하는 것은 “작업대 없이 공장에만 최종본을 방치”하는 것이다.

```text
[1 GENERATE]  stories/<ep>/  ·  (스모크) F:\generated_*  ·  Comfy input/output temps
      ↓
[2 EXPORT]    AGENT_WORKSPACE/episodes/<ep>/   ← 의무 (또는 -o 로 처음부터 작업대)
      ↓
[3 CLEANUP]   factory_cleanup --scope session|episode
```

| 단계 | 어디에 남아도 되나 | 에이전트 의무 |
|------|-------------------|---------------|
| 생성 중 | `stories/<ep>/`, 스모크 덤프, Comfy temp | 경로를 기록 |
| 세션 끝 | **작업대에 복사본** | `export_episode_to_workspace` 또는 `-o` |
| 정리 | 공장 스모크/temp 삭제 OK | `factory_cleanup` |

### 6.1 정리 CLI

```bash
# 기본: dry-run (무엇을 지울지 출력)
python scripts/factory_cleanup.py --scope session

# 실제 삭제: 스모크 덤프 + Comfy temp + archive logs
python scripts/factory_cleanup.py --scope session --apply

# 에피소드 스테이징 삭제 (export 마커 있을 때만)
python scripts/export_episode_to_workspace.py -e EP
python scripts/factory_cleanup.py --scope episode -e EP --apply
```

| scope | 대상 |
|-------|------|
| `smoke` | `F:\generated_images` / `F:\generated_videos` 의 `ab_*`, `*smoke*`, `agent_*` 등 |
| `comfy` | Comfy `input/temp_*`, `output/agent_*` |
| `logs` | `scripts/_archive/tmp/*.out.txt`, 프리셋 백업 폴더 |
| `session` | smoke + comfy + logs (**세션 종료 기본**) |
| `episode` | `stories/<ep>/` (export 마커 또는 `AGENT_CLEANUP_FORCE_EPISODE=1`) |

**절대 자동 삭제 안 함:** `workflows/`, `characters/`, `locations/`, `looks/`, `skills/`, 코드.

### 6.2 완료 보고에 cleanup 한 줄

```text
workspace_copy: <AGENT_WORKSPACE>/episodes/<ep>
factory_cleanup: session applied | dry-run | skipped
```

---

## 7. 한 줄 요약

```text
RUN tools from agent_custom → READ paths → COPY to YOUR workspace → CLEANUP factory staging
Staging on the factory floor is OK; abandoning finals there is not.
```

