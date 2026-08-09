# Advanced_V37 — Agent 선택 가이드

> **Shelf:** GENERATE / TRANSFORM (pose·IPA)  
> **CLI:** `python scripts/generate_illustrious_advanced.py`  
> **Sibling:** Standard = daily · **Detailer** = existing-image specialty  
> **SSOT UI:** `Advanced_V37.json`

## 언제 쓰나

| 필요 | 도구 |
|------|------|
| 일상 애니 한 장 | **Standard** (`generate_illustrious_standard`) |
| **TIPO** 태그 확장 | **Advanced** `--tipo` |
| **OpenPose** 포즈 고정 | **Advanced** `--openpose pose.png` |
| **IPAdapter** 얼굴/스타일 레퍼 | **Advanced** `--ipa` / `--style-image` |
| **Regional** 멀티 프롬프트 | **Advanced** `--regional` |
| 기존 컷 인페/아웃페 | **Detailer** |

## 빠른 시작

```bash
python scripts/generate_illustrious_advanced.py --list-features

# 기본 (Face + SAM + CLIP skip + NegPip)
python scripts/generate_illustrious_advanced.py \
  -p "masterpiece, best quality, 1girl, solo, portrait" -o out.png --seed 42

# TIPO
python scripts/generate_illustrious_advanced.py -p "1girl, ..." --tipo -o out.png

# OpenPose
python scripts/generate_illustrious_advanced.py -p "1girl, ..." --openpose pose.png -o out.png

# IP-Adapter face ref
python scripts/generate_illustrious_advanced.py -p "1girl, ..." --ipa face.png -o out.png
```

## 구현 정책

- 실 UI + Fast Groups `mode` 0/4 토글 → expand → port inject  
- Standard에 TIPO/IPA/Pose를 **가짜로 넣지 않음**  
- 체크포인트 bare name → `Illustrious\…` 자동 리맵  

기계 메뉴: `CAPABILITIES.json` · 그룹: `GROUPS.json`
