# Detailer_V37 — Agent 선택 가이드

> **Shelf:** FINISH / TRANSFORM  
> **CLI:** `python scripts/generate_illustrious_detailer.py -i still.png -o out.png`  
> **SSOT UI:** `Detailer_V37.json`

## 언제 쓰나

| 필요 | 도구 |
|------|------|
| 생성하면서 Face/Hand | Standard / Advanced 내 ADetailer |
| **이미 있는 이미지** 얼굴·손·눈 정리 | **Detailer** (기본 face+mask) |
| **Inpaint / Outpaint** | **Detailer** `--inpaint` / `--outpaint` |
| 워터마크·압축 제거 | `--remove-watermark` · `--fbcnn` |
| 배경 제거 | `--rmbg` |

## 빠른 시작

```bash
python scripts/generate_illustrious_detailer.py --list-features

# 기본 폴리시 (Face + Mask ADetailer)
python scripts/generate_illustrious_detailer.py -i still.png -o polished.png

# 손·눈
python scripts/generate_illustrious_detailer.py -i still.png -o out.png --hand --eyes

# 인페 / 아웃페
python scripts/generate_illustrious_detailer.py -i still.png -o out.png --inpaint -p "fix hands, detailed"
# 마스크 파일 (흰색=수정 영역) → 알파로 합성 후 Inpaint
python scripts/generate_illustrious_detailer.py -i still.png --mask mask.png --inpaint \
  -p "fix hands, detailed" -o out.png
python scripts/generate_illustrious_detailer.py -i still.png -o out.png --outpaint

# 의존성
python scripts/illustrious_check.py --pack detailer
python scripts/generate_illustrious_detailer.py --check-models
```

## 주의

- **반드시 `-i` 입력 이미지**  
- `--mask` 는 흰색=편집 영역 (LoadImage 알파/MASK 슬롯). `--mask-invert` 로 반전 가능  
- Inpaint CN: `models/controlnet/noobaiInpainting_v10.safetensors`  
- 18+ NSFW detailer는 `--i-am-18` 필수  

기계 메뉴: `CAPABILITIES.json` · 그룹: `GROUPS.json`
