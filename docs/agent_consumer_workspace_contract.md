# 에이전트 소비자 계약 — 도구 저장소 vs 내 작업 디렉터리

- **대상**: 이 레포(`agent_custom`)의 CLI를 **호출만** 하는 에이전트 (코딩 에이전트·제작 에이전트)
- **문제**: 산출물이 `stories/`·`characters/` 등 **도구 레포 기본 경로**에만 남고, 에이전트 자신의 프로젝트 폴더로 안 가져옴 → 이후 편집·납품이 끊김
- **관련**: [agent_av_smoke_checklist.md](agent_av_smoke_checklist.md), [agent_rules.md](../agent_rules.md)

---

## 1. 한 줄 규칙

> **도구 레포 = 공장.**  
> **에이전트 작업 디렉터리 = 작업대.**  
> 공장에서 뽑은 물건은 **작업대로 가져와야** 지지고 볶을 수 있다. 공장 바닥에 두고 끝내지 마라.

---

## 2. 경로 SSOT

| 구분 | 경로 (도구 레포 루트 기준) | 의미 |
|------|---------------------------|------|
| 도구 코드 | `scripts/`, `lib/`, `workflows/agent/` | 실행만. 여기다 프로젝트 파일을 쌓지 말 것 |
| 에피소드 작업실 | `stories/<episode_id>/` | 키프레임·clips·audio·exports **생성 기본 위치** |
| 캐릭/로케 | `characters/`, `locations/` | 공유 자산 팩 |
| 납품 상자 | `deliveries/` | zip 등 (있을 때) |
| **에이전트 작업대** | **호출 측이 정한 디렉터리** | 예: `../my_film/`, `C:/work/client_x/` |

`StoryPackage` / 대부분 CLI는 **`agent_custom` 루트를 cwd로** 두고 `stories/<ep>/...` 에 쓴다.  
**다른 에이전트의 프로젝트 루트와 자동 동기화되지 않는다.**

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

### 3.2 생성 직후 (의무)

`AGENT_RESULT` / 메타에 나온 **artifacts 경로를 읽고**:

1. **작업대로 복사**하거나  
2. 처음부터 `-o` / `--output` 으로 **작업대 절대 경로**를 지정한다.

```bash
# 권장: 에피소드 통째 스냅샷을 내 작업대로
python scripts/export_episode_to_workspace.py -e my_ep \
  --dest "D:/projects/client_film/inbox/my_ep"

# 또는 단일 파일
python scripts/generate_i2v.py -i ... -o "D:/projects/client_film/clips/S01.mp4" ...
```

### 3.3 금지

- 산출물 경로를 읽지 않고 “생성 끝”으로 보고  
- `stories/` 안에만 두고 사용자 프로젝트에 반영하지 않음  
- 도구 레포를 git commit 할 때 대용량 생성물 무분별 추가 (stories 등은 종종 gitignore)

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
| `AGENT_COMFY_LAUNCH_BAT` | Comfy 기동 bat (기본 `F:\ComfyUI_windows_portable\run_nvidia_gpu_fast_fp16_accumulation.bat`) |
| `AGENT_COMFY_READY_TIMEOUT_SEC` | 기동 후 API ready 대기 초 (기본 180) |

```bash
set AGENT_WORKSPACE=D:\projects\client_film
python scripts/export_episode_to_workspace.py -e my_ep
# → %AGENT_WORKSPACE%/episodes/my_ep/ 또는 --dest
```

---

## 6. 한 줄 요약

```text
RUN tools from agent_custom → READ artifact paths → COPY into YOUR workspace → THEN edit/deliver
Never leave final work only under stories/ inside the tool repo.
```
