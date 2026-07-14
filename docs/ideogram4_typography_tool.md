# Ideogram 4 타이포 도구 (에이전트)

- **작성**: 2026-07-14  
- **상태**: ✅ CLI 1차 (`scripts/generate_ideogram4.py`)  
- **역할**: 이미지 안 **글자/간판/포스터/타이틀 카드** 특화 T2I  
- **비역할**: 전 구간 일반 T2I 교체 금지 (Moody / Krea / Z-Image 유지)

관련: [agent_video_tooling_reliability.md](agent_video_tooling_reliability.md) §11.2 · [agent_video_tooling_todo.md](agent_video_tooling_todo.md)

---

## 1. 언제 쓰나

| 슬롯 (`--slot`) | 용도 |
|-----------------|------|
| `title_card` | 쇼츠 오프닝 타이틀 |
| `end_card` | 엔딩/구독 카드 |
| `menu_board` | 카페 메뉴판 실사 레퍼 |
| `signage` | 로케 간판 레퍼 |
| `thumbnail` | 썸네일용 큰 글자 |
| `free` | 자유 캡션 / 전체 JSON |

일반 캐릭·키프레임·무드 컷은 **기존 엔진**을 쓴다.

---

## 2. 모델 설치

```
ComfyUI/models/
  diffusion_models/Ideogram4/
    ideogram4_fp8_scaled.safetensors
    ideogram4_unconditional_fp8_scaled.safetensors
  text_encoders/
    qwen3vl_8b_fp8_scaled.safetensors   # ~8GB, 필수
  vae/
    flux2-vae.safetensors
```

- Comfy-Org: [Ideogram-4](https://huggingface.co/Comfy-Org/Ideogram-4) · [Qwen3-VL](https://huggingface.co/Comfy-Org/Qwen3-VL) · [flux2-dev VAE](https://huggingface.co/Comfy-Org/flux2-dev)
- 검사: `python scripts/generate_ideogram4.py --check-models`
- Comfy 노드: `Ideogram4Scheduler`, `DualModelGuider`, `EmptyFlux2LatentImage`, CLIP type `ideogram4`

**라이선스**: Ideogram Non-Commercial Model Agreement — 상업 배포 전 확인.

---

## 3. CLI

```bash
# 쇼츠 타이틀 카드 (9:16)
python scripts/generate_ideogram4.py \
  --slot title_card \
  --text "채널 주인장이 뭐해야 할지모르겠답니다" \
  --subtitle "카페 고민 EP.01" \
  --scene "soft quiet luxury daytime, warm cream and sage" \
  --aspect 9:16 --profile default \
  -o F:/generated_images/title_cafe_gomin.png

# 메뉴판 레퍼
python scripts/generate_ideogram4.py \
  --slot menu_board \
  --text "Americano 4.5 / Latte 5.0 / Affogato 6.5" \
  --scene "sunlit wooden cafe counter" \
  -o stories/cafe_gomin_ep01/refs/menu_board.png

# 캡션만 미리보기
python scripts/generate_ideogram4.py --slot signage --text "테라스 카페" --dump-caption

# 전체 JSON 캡션 파일
python scripts/generate_ideogram4.py --json my_caption.json -o out.png
```

| 플래그 | 설명 |
|--------|------|
| `--slot` | 레이아웃 레시피 |
| `--text` / `--subtitle` | **철자 고정** 온이미지 문구 |
| `--scene` | 배경·무드 |
| `--aspect` | `9:16` `1:1` `16:9` `shorts` … |
| `--profile` | `turbo` 12step · `default` 20 · `quality` 48 |
| `--palette` | `#hex,#hex` |
| `--json` / `--json-inline` | 풀 구조화 캡션 |
| `--dry-run` | 큐 없이 캡션 확인 |
| `--check-models` | 가중치 존재·용량 |

코드: `lib/ideogram4_prompt.py` (캡션 빌더) · `scripts/generate_ideogram4.py` (API 그래프).

---

## 4. 프롬프트 팁 (스키마 필수)

공식: [ideogram-oss prompting](https://github.com/ideogram-oss/ideogram4/blob/main/docs/prompting.md)

1. **구조화 JSON이 본선** — 평문만 쓰면 safety filter 오탐↑.  
2. 글자는 element **`type: "text"`** + 별도 **`text`** 필드 (desc에만 쓰면 철자 붕괴).  
3. **bbox** = `[y_min, x_min, y_max, x_max]` 정규화 **0–1000** (픽셀 xy 아님).  
4. `--text`에 그대로 나올 철자, 장식은 `--scene`.  
5. 한글은 짧은 헤드라인이 유리. 실패 시 `quality` 프로필·시드 재시도.  
6. 첫 스모크(turbo+obj type)는 글자가 깨질 수 있음 → **스키마 수정 후 quality 재생성**.

---

## 5. 에피소드 연동 (관례)

| 경로 | 용도 |
|------|------|
| `stories/<ep>/refs/title_card.png` | 오프닝 스틸 |
| `stories/<ep>/refs/end_card.png` | 엔딩 |
| `locations/<id>/refs/signage_*.png` | 간판 레퍼 |
| meta `*.json` | seed·caption·slot 기록 |

별도 `episode_typo.py` 는 필요해지면 얇게 추가 (지금은 생성 CLI로 충분).

---

## 6. 품질 프리셋

| profile | steps | mu | std | cfg |
|---------|-------|----|-----|-----|
| turbo | 12 | 0.5 | 1.75 | 7 |
| default | 20 | 0.0 | 1.75 | 7 |
| quality | 48 | 0.0 | 1.5 | 7 |

---

## 7. 알려진 제약

- VRAM: 4090 24GB 급에서 FP8 운용 전제. 다른 대형 모델 로드 중이면 unload 후 실행.  
- 글자 완벽 보장은 없음 — 중요 문구는 생성 여러 시드 또는 수동 검수.  
- 본 도구는 **영상 립/모션 파이프와 독립**. AV smoke 게이트에 포함하지 않음.
