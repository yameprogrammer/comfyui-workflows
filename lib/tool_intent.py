"""
Intent → tool router for the agent toolbox (discovery only, no Comfy).

Agents ask: "I want X — which CLI?" This module ranks catalog intents by keywords.
Each card includes:
  - examples[]  : one-line copy-paste CLI
  - alternatives[] : {if, use, cli} when this tool fails or is wrong choice

Human SSOT: docs/tool_catalog.md · card standard: docs/toolbox_card_standard.md
"""

from __future__ import annotations

import re
from typing import Any

# Card fields: id, shelf, cli, script, summary, when, when_not,
# keywords, examples, alternatives[{if, use, cli}]
INTENT_TOOLS: list[dict[str, Any]] = [
    {
        "id": "still_photoreal",
        "shelf": "GENERATE",
        "cli": "python scripts/generate_krea.py",
        "script": "generate_krea.py",
        "summary": "실사 시네 스틸 T2I (기본: Krea2)",
        "when": "텍스트만으로 인물/무드 한 장 — 시네·패션·키프레임 기본",
        "when_not": "애니 태그 → Illustrious · 18+ → krea_nsfw · I2I denoise 실험 → moody",
        "keywords": [
            "t2i", "still", "photo", "photoreal", "portrait", "실사", "스틸",
            "키프레임", "생성", "한장", "krea", "krea2", "시네", "인물",
        ],
        "examples": [
            'python scripts/generate_krea.py -p "cinematic portrait of a woman" -o out.png --seed 42',
            'python scripts/generate_krea.py -p "..." --lora Krea2\\\\krea2_darkbrush.safetensors --lora-strength 0.7 -o out.png',
            'python scripts/generate_krea.py -p "..." --rebalance --rebalance-mult 2.0 -o out.png',
            "python scripts/krea2_features.py list --ready",
            "python scripts/krea2_features.py search \"style control detailer\"",
        ],
        "alternatives": [
            {"if": "I2I denoise·스타일 실험", "use": "moody T2I/I2I", "cli": "python scripts/generate_moody.py -m pro -p \"...\" -o out.png"},
            {"if": "애니/일루스 태그", "use": "Illustrious XL", "cli": "python scripts/generate_illustrious_standard.py -p \"1girl, ...\" -o out.png"},
            {"if": "18+ NSFW", "use": "Krea NSFW", "cli": "python scripts/generate_krea_nsfw.py -p \"...\" -o out.png"},
            {"if": "레퍼 얼굴 유지하며 장면만 변경", "use": "character_consistent", "cli": "python scripts/generate_character_consistent.py --mode lock -i face.png -p \"...\" -o out.png"},
            {"if": "Lonecat Krea2 v7 전체 기능 맵", "use": "krea2_features", "cli": "python scripts/krea2_features.py list"},
        ],
    },
    {
        "id": "krea2_features",
        "shelf": "META",
        "cli": "python scripts/krea2_features.py",
        "script": "krea2_features.py",
        "summary": "Lonecat Krea2 v7.0 + v10 기능 인벤토리 (바이패스 맵)",
        "when": "Krea2/Lonecat v7 토글·스타일·디테일러·무드보드 중 무엇을 쓸지 모를 때",
        "when_not": "이미 generate_krea로 T2I만 하면 될 때",
        "keywords": [
            "krea2", "lonecat krea", "v7", "v70", "moodboard", "style reference",
            "krea feature", "bypass", "detailer", "krea2_features", "기능 목록",
        ],
        "examples": [
            "python scripts/krea2_features.py list",
            "python scripts/krea2_features.py list --ready",
            "python scripts/krea2_features.py routes",
            "python scripts/krea2_features.py search \"style\"",
            "python scripts/krea2_features.py show v70_controlnet",
        ],
        "alternatives": [
            {"if": "실사 T2I 바로", "use": "generate_krea", "cli": "python scripts/generate_krea.py -p \"...\" -o out.png"},
            {"if": "Krea2 네이티브 스타일 레퍼", "use": "krea2_style", "cli": "python scripts/generate_krea2_style.py -i style.png -p \"...\" -o out.png"},
            {"if": "Krea2 ControlLoRA", "use": "krea2_control", "cli": "python scripts/generate_krea2_control.py -i depth.png -p \"...\" -o out.png"},
            {"if": "지시 편집", "use": "qwen_edit", "cli": "python scripts/generate_qwen_edit.py -i img.png -p \"...\" -o out.png"},
        ],
    },
    {
        "id": "krea2_style",
        "shelf": "TRANSFORM",
        "cli": "python scripts/generate_krea2_style.py",
        "script": "generate_krea2_style.py",
        "summary": "Krea2 네이티브 스타일 레퍼런스 T2I",
        "when": "스타일 이미지 룩을 유지하며 텍스트로 새 장면 생성 (Lonecat v7 StyleReference)",
        "when_not": "픽셀 I2I denoise → krea2_i2i / moody · 포즈 구조 → krea2_control",
        "keywords": [
            "krea style", "style reference", "krea2 style", "스타일 레퍼", "무드 레퍼",
            "generate_krea2_style", "style transfer krea",
        ],
        "examples": [
            'python scripts/generate_krea2_style.py -i style.png -p "cinematic portrait..." -o out.png --seed 42',
            "python scripts/generate_krea2_style.py -i mood.png -p \"...\" -o out.png --style-strength 0.85",
            'python scripts/generate_krea2_style.py -i a.png --style-image-2 b.png -p "fashion portrait" -o dual.png',
        ],
        "alternatives": [
            {"if": "일반 스타일 전이 (비-Krea)", "use": "style_transfer", "cli": "python scripts/generate_style_transfer.py --mode ref -i c.png --style-image s.png -o out.png"},
            {"if": "스타일 없이 T2I", "use": "generate_krea", "cli": "python scripts/generate_krea.py -p \"...\" -o out.png"},
            {"if": "구조/뎁스 제어", "use": "krea2_control", "cli": "python scripts/generate_krea2_control.py -i depth.png -p \"...\" -o out.png"},
            {"if": "이미지 캡션 후 생성", "use": "krea2_img_prompt", "cli": "python scripts/generate_krea2_img_prompt.py -i ref.png -o out.png"},
        ],
    },
    {
        "id": "krea2_img_prompt",
        "shelf": "GENERATE",
        "cli": "python scripts/generate_krea2_img_prompt.py",
        "script": "generate_krea2_img_prompt.py",
        "summary": "이미지 → Florence 캡션 → Krea2 T2I",
        "when": "레퍼 스틸에서 프롬프트를 뽑고 같은 룩으로 새 장 생성 (v7 Img Prompt)",
        "when_not": "이미 프롬프트가 있음 → generate_krea · 픽셀 I2I → krea2_i2i",
        "keywords": [
            "img prompt", "image to prompt", "florence", "caption", "이미지 프롬프트",
            "캡션", "generate_krea2_img_prompt", "img2prompt",
        ],
        "examples": [
            "python scripts/generate_krea2_img_prompt.py -i ref.png -o out.png --seed 42",
            "python scripts/generate_krea2_img_prompt.py -i ref.png --caption-only",
            'python scripts/generate_krea2_img_prompt.py -i ref.png -o out.png --extra "cinematic night"',
        ],
        "alternatives": [
            {"if": "텍스트만", "use": "generate_krea", "cli": "python scripts/generate_krea.py -p \"...\" -o out.png"},
            {"if": "스타일 이미지 직접", "use": "krea2_style", "cli": "python scripts/generate_krea2_style.py -i style.png -p \"...\" -o out.png"},
        ],
    },
    {
        "id": "krea2_face_detail",
        "shelf": "FINISH",
        "cli": "python scripts/generate_krea2_face_detail.py",
        "script": "generate_krea2_face_detail.py",
        "summary": "스틸 얼굴 디테일러 (Impact FaceDetailer + Krea2)",
        "when": "T2I 후 얼굴 선명도/디테일 보정 (v7 Face detailer 대응)",
        "when_not": "전신 해상도 업 → upscale_image · 손 → krea2_hand_detail",
        "keywords": [
            "face detailer", "facedetail", "얼굴 보정", "krea face",
            "generate_krea2_face_detail", "impact face",
        ],
        "examples": [
            "python scripts/generate_krea2_face_detail.py -i still.png -o face.png --seed 42",
            "python scripts/generate_krea2_face_detail.py -i still.png -o out.png --denoise 0.22",
        ],
        "alternatives": [
            {"if": "손 보정", "use": "krea2_hand_detail", "cli": "python scripts/generate_krea2_hand_detail.py -i still.png -o hands.png"},
            {"if": "전체 업스케일", "use": "upscale_image", "cli": "python scripts/upscale_image.py -i still.png -o out.png --style photo --preset deliver_1080"},
            {"if": "새로 생성", "use": "generate_krea", "cli": "python scripts/generate_krea.py -p \"...\" -o out.png"},
        ],
    },
    {
        "id": "krea2_hand_detail",
        "shelf": "FINISH",
        "cli": "python scripts/generate_krea2_hand_detail.py",
        "script": "generate_krea2_hand_detail.py",
        "summary": "스틸 손 디테일러 (hand YOLO + DetailerForEach)",
        "when": "손이 프레임에 보일 때 손가락/손 디테일 보정",
        "when_not": "손이 안 보이면 스킵 · 얼굴만 → face_detail",
        "keywords": [
            "hand detailer", "hands", "손가락", "손 보정", "generate_krea2_hand_detail",
        ],
        "examples": [
            "python scripts/generate_krea2_hand_detail.py -i still_hands.png -o hands.png --seed 42",
            "python scripts/generate_krea2_hand_detail.py -i still.png -o out.png --denoise 0.28 --threshold 0.3",
        ],
        "alternatives": [
            {"if": "얼굴 보정", "use": "krea2_face_detail", "cli": "python scripts/generate_krea2_face_detail.py -i still.png -o face.png"},
        ],
    },
    {
        "id": "krea2_moodboard",
        "shelf": "GENERATE",
        "cli": "python scripts/generate_krea2_moodboard.py",
        "script": "generate_krea2_moodboard.py",
        "summary": "Krea Moodboard 검색 → 프롬프트 확장 → T2I",
        "when": "무드/팔레트 키워드로 룩을 붙인 뒤 Krea 스틸 생성",
        "when_not": "이미 완성 프롬프트 → generate_krea · 이미지 스타일 레퍼 → krea2_style",
        "keywords": [
            "moodboard", "krea moodboard", "무드보드", "golden hour", "palette",
            "generate_krea2_moodboard",
        ],
        "examples": [
            'python scripts/generate_krea2_moodboard.py --query "golden hour cinematic" --prompt "portrait of a woman" -o out.png --seed 42',
            'python scripts/generate_krea2_moodboard.py --query "dark teal gothic" --prompt "hero standing" --prompt-only',
        ],
        "alternatives": [
            {"if": "스타일 이미지 있음", "use": "krea2_style", "cli": "python scripts/generate_krea2_style.py -i style.png -p \"...\" -o out.png"},
            {"if": "텍스트만", "use": "generate_krea", "cli": "python scripts/generate_krea.py -p \"...\" -o out.png"},
        ],
    },
    {
        "id": "rmbg",
        "shelf": "FINISH",
        "cli": "python scripts/generate_rmbg.py",
        "script": "generate_rmbg.py",
        "summary": "배경 제거 (u2net human seg)",
        "when": "인물/피사체 컷아웃 (합성 전처리)",
        "when_not": "전경 품질 보정 → face/hand detail 먼저",
        "keywords": [
            "rmbg", "remove background", "배경 제거", "cutout", "rembg", "generate_rmbg",
        ],
        "examples": [
            "python scripts/generate_rmbg.py -i person.png -o cutout.png",
        ],
        "alternatives": [
            {"if": "얼굴 보정 먼저", "use": "krea2_face_detail", "cli": "python scripts/generate_krea2_face_detail.py -i still.png -o face.png"},
            {"if": "색 보정", "use": "krea2_color_match", "cli": "python scripts/generate_krea2_color_match.py -i still.png --ref mood.png -o out.png"},
        ],
    },
    {
        "id": "krea2_post",
        "shelf": "FINISH",
        "cli": "python scripts/generate_krea2_post.py",
        "script": "generate_krea2_post.py",
        "summary": "가벼운 포스트 폴리시 (BC + film grain + Lucy sharpen)",
        "when": "최종 스틸 톤/샤픈/그레인 살짝 (v7 post suite 슬라이스)",
        "when_not": "해상도 업 → upscale_image · 색 레퍼 매칭 → krea2_color_match · 얼굴 → face_detail",
        "keywords": [
            "post polish", "film grain", "sharpen", "krea post", "generate_krea2_post",
            "그레인", "샤픈", "포스트", "polish",
        ],
        "examples": [
            "python scripts/generate_krea2_post.py -i still.png -o polished.png",
            "python scripts/generate_krea2_post.py -i still.png -o out.png --contrast 1.08 --grain 0.2",
        ],
        "alternatives": [
            {"if": "색 레퍼 맞추기", "use": "krea2_color_match", "cli": "python scripts/generate_krea2_color_match.py -i still.png --ref mood.png -o out.png"},
            {"if": "배경 제거", "use": "rmbg", "cli": "python scripts/generate_rmbg.py -i person.png -o cutout.png"},
            {"if": "업스케일", "use": "upscale_image", "cli": "python scripts/upscale_image.py -i still.png -o out.png --style photo --preset deliver_1080"},
        ],
    },
    {
        "id": "krea2_color_match",
        "shelf": "FINISH",
        "cli": "python scripts/generate_krea2_color_match.py",
        "script": "generate_krea2_color_match.py",
        "summary": "타겟 이미지를 레퍼 룩에 ColorMatch (mkl)",
        "when": "무드/그레이딩 레퍼 사진에 색 맞추기 (LUT 대용 경량)",
        "when_not": "스타일 구조까지 바꾸기 → krea2_style · 단순 밝기/그레인 → krea2_post",
        "keywords": [
            "color match", "colormatch", "color grade", "look match", "generate_krea2_color_match",
            "컬러매치", "색 보정", "그레이딩", "grade",
        ],
        "examples": [
            "python scripts/generate_krea2_color_match.py -i target.png --ref mood.png -o out.png",
            "python scripts/generate_krea2_color_match.py -i target.png --ref mood.png -o out.png --strength 0.5",
        ],
        "alternatives": [
            {"if": "가벼운 그레인/샤픈만", "use": "krea2_post", "cli": "python scripts/generate_krea2_post.py -i still.png -o out.png"},
            {"if": "스타일 이미지로 생성", "use": "krea2_style", "cli": "python scripts/generate_krea2_style.py -i style.png -p \"...\" -o out.png"},
        ],
    },
    {
        "id": "krea_draft",
        "shelf": "GENERATE",
        "cli": "python scripts/generate_krea_draft.py",
        "script": "generate_krea_draft.py",
        "summary": "Krea2 빠른 드래프트/스카우트 T2I (기본 768²)",
        "when": "구도·시드 스카우트 후 최종 1024로 승격",
        "when_not": "납품 품질 최종 → generate_krea (1024+) · 스타일 레퍼 → krea2_style",
        "keywords": [
            "draft", "scout", "rough", "krea draft", "generate_krea_draft",
            "드래프트", "스카우트", "러프",
        ],
        "examples": [
            'python scripts/generate_krea_draft.py -p "cinematic portrait..." -o scout.png --seed 1',
            "python scripts/generate_krea_draft.py -p \"...\" -o scout.png --width 640 --height 640",
        ],
        "alternatives": [
            {"if": "최종 품질", "use": "still_photoreal", "cli": "python scripts/generate_krea.py -p \"...\" -o out.png --seed 42"},
            {"if": "무드보드 키워드", "use": "krea2_moodboard", "cli": 'python scripts/generate_krea2_moodboard.py --query "golden hour" --prompt "portrait" -o out.png'},
        ],
    },
    {
        "id": "krea2_region_detail",
        "shelf": "FINISH",
        "cli": "python scripts/generate_krea2_region_detail.py",
        "script": "generate_krea2_region_detail.py",
        "summary": "Krea2 v7 영역 디테일러 (Eyes/Spare/Breasts/Body/Male/Vajayjay)",
        "when": "UI detailer 그룹 대응 — 눈·스페어·NSFW 부위 보정",
        "when_not": "전신 재생성 → generate_krea · 얼굴 전용 전용툴 → face_detail · 손 → hand_detail",
        "keywords": [
            "region detailer", "eyes detailer", "spare detailer", "breasts detailer",
            "female body", "male junk", "vajayjay", "generate_krea2_region_detail",
            "krea2 eyes", "디테일러 영역", "눈 보정",
        ],
        "examples": [
            "python scripts/generate_krea2_region_detail.py --list",
            "python scripts/generate_krea2_region_detail.py -i still.png -o eyes.png --region eyes",
            "python scripts/generate_krea2_region_detail.py -i still.png -o out.png --region spare --sam-prompt \"necklace\"",
            "python scripts/generate_krea2_region_detail.py -i nsfw.png -o out.png --region breasts --i-am-18",
            "python scripts/generate_krea2_region_detail.py -i nsfw.png -o out.png --region female_body --i-am-18",
            "python scripts/generate_krea2_region_detail.py -i nsfw.png -o out.png --region male_junk --i-am-18",
            "python scripts/generate_krea2_region_detail.py -i nsfw.png -o out.png --region vajayjay --i-am-18",
        ],
        "alternatives": [
            {"if": "눈만 단축", "use": "krea2_eyes_detail", "cli": "python scripts/generate_krea2_eyes_detail.py -i still.png -o eyes.png"},
            {"if": "얼굴", "use": "krea2_face_detail", "cli": "python scripts/generate_krea2_face_detail.py -i still.png -o face.png"},
            {"if": "손", "use": "krea2_hand_detail", "cli": "python scripts/generate_krea2_hand_detail.py -i still.png -o hands.png"},
        ],
    },
    {
        "id": "krea2_eyes_detail",
        "shelf": "FINISH",
        "cli": "python scripts/generate_krea2_eyes_detail.py",
        "script": "generate_krea2_eyes_detail.py",
        "summary": "눈 디테일러 (SAM3 기본 / Eyeful YOLO 옵션)",
        "when": "인물 스틸 눈동자·홍채 선명도 보정 (v7 Eyes 그룹)",
        "when_not": "얼굴 전체 → face_detail · 임의 부위 → region spare",
        "keywords": [
            "eyes detailer", "eye detail", "eyeful", "generate_krea2_eyes_detail",
            "눈 보정", "눈동자",
        ],
        "examples": [
            "python scripts/generate_krea2_eyes_detail.py -i still.png -o eyes.png",
            "python scripts/generate_krea2_eyes_detail.py -i still.png -o eyes.png --engine yolo",
        ],
        "alternatives": [
            {"if": "얼굴 전체", "use": "krea2_face_detail", "cli": "python scripts/generate_krea2_face_detail.py -i still.png -o face.png"},
            {"if": "다른 영역", "use": "krea2_region_detail", "cli": "python scripts/generate_krea2_region_detail.py --list"},
        ],
    },
    {
        "id": "krea2_anatomy_detail",
        "shelf": "FINISH",
        "cli": "python scripts/generate_krea2_anatomy_detail.py",
        "script": "generate_krea2_anatomy_detail.py",
        "summary": "18+ 해부학 영역 디테일러 (region_detail 래퍼)",
        "when": "성인 스틸 부위 보정 — breasts/female_body/male_junk/vajayjay/penis — **--i-am-18**",
        "when_not": "미성년·SFW · 눈/스페어 → region_detail · 얼굴/손 → face/hand",
        "keywords": [
            "anatomy detailer", "nsfw detailer", "generate_krea2_anatomy_detail",
            "해부학", "디테일러 18", "adult detail", "breasts", "vajayjay",
        ],
        "examples": [
            "python scripts/generate_krea2_anatomy_detail.py -i nsfw.png -o out.png --region breasts --i-am-18",
            "python scripts/generate_krea2_anatomy_detail.py -i nsfw.png -o out.png --region male_junk --i-am-18",
            "python scripts/generate_krea2_anatomy_detail.py -i nsfw.png -o out.png --region vagina --i-am-18",
        ],
        "alternatives": [
            {"if": "전체 영역 목록", "use": "krea2_region_detail", "cli": "python scripts/generate_krea2_region_detail.py --list"},
            {"if": "얼굴", "use": "krea2_face_detail", "cli": "python scripts/generate_krea2_face_detail.py -i still.png -o face.png"},
            {"if": "전체 NSFW 생성", "use": "still_nsfw", "cli": 'python scripts/generate_krea_nsfw.py -p "adult..." -o out.png'},
        ],
    },
    {
        "id": "krea2_control",
        "shelf": "CAMERA",
        "cli": "python scripts/generate_krea2_control.py",
        "script": "generate_krea2_control.py",
        "summary": "Krea2 ControlLoRA (depth/structure) T2I",
        "when": "뎁스·구조·포즈 맵으로 Krea2 생성 제어 (v7 Control 경로)",
        "when_not": "OpenPose 스틸 템플릿 → openpose_pose · 스타일 룩만 → krea2_style",
        "keywords": [
            "krea control", "control lora", "depth control", "krea2 control",
            "구조 제어", "뎁스", "generate_krea2_control", "controllora",
        ],
        "examples": [
            'python scripts/generate_krea2_control.py -i depth.png -p "hero standing..." -o out.png --seed 42',
            "python scripts/generate_krea2_control.py -i pose.png -p \"...\" -o out.png --control-strength 0.9",
        ],
        "alternatives": [
            {"if": "OpenPose 템플릿 스틸", "use": "openpose_pose", "cli": "python scripts/generate_openpose_pose.py generate -i id.png --template jog_contact -o out.png"},
            {"if": "스타일 레퍼", "use": "krea2_style", "cli": "python scripts/generate_krea2_style.py -i style.png -p \"...\" -o out.png"},
            {"if": "자유 T2I", "use": "generate_krea", "cli": "python scripts/generate_krea.py -p \"...\" -o out.png"},
        ],
    },
    {
        "id": "still_anime",
        "shelf": "GENERATE",
        "cli": "python scripts/generate_illustrious_standard.py",
        "script": "generate_illustrious_standard.py",
        "summary": "애니/일루스 XL Standard_V37 (실 UI + Fast Groups 스위치)",
        "when": "Danbooru 태그·Illustrious/NoobAI 체크포인트 스틸·I2I·ADetailer·Hires",
        "when_not": "실사 photoreal → generate_krea · TIPO/IPA/OpenPose → still_anime_advanced · 기존컷 인페 → still_anime_detailer",
        "keywords": [
            "anime", "illustrious", "애니", "일러", "만화", "xl", "태그",
            "standard_v37", "noobai", "adetailer", "hires", "generate_illustrious",
            "fabricated", "danbooru",
        ],
        "examples": [
            'python scripts/generate_illustrious_standard.py -p "masterpiece, best quality, 1girl, solo, portrait" -o out.png --seed 42',
            "python scripts/illustrious_check.py --pack all",
            "python scripts/generate_illustrious_standard.py --list-features",
            "python scripts/generate_illustrious_standard.py --check-models",
            'python scripts/generate_illustrious_standard.py -p "..." --hand --eyes --hires-post -o out.png',
            "python scripts/generate_illustrious_standard.py -i ref.png -p \"...\" -d 0.55 -o i2i.png",
            "python scripts/generate_illustrious_standard.py --preset t2i_clean -p \"...\" -o draft.png",
        ],
        "alternatives": [
            {"if": "TIPO/IPA/OpenPose", "use": "still_anime_advanced", "cli": "python scripts/generate_illustrious_advanced.py --list-features"},
            {"if": "기존 이미지 인페/아웃페", "use": "still_anime_detailer", "cli": "python scripts/generate_illustrious_detailer.py -i still.png -o out.png"},
            {"if": "실사 인물", "use": "krea SFW", "cli": "python scripts/generate_krea.py -p \"...\" -o out.png"},
            {"if": "사진→애니 레스타일", "use": "style_transfer", "cli": "python scripts/generate_style_transfer.py --mode preset --style anime -i photo.png -o out.png"},
        ],
    },
    {
        "id": "still_anime_advanced",
        "shelf": "GENERATE",
        "cli": "python scripts/generate_illustrious_advanced.py",
        "script": "generate_illustrious_advanced.py",
        "summary": "Illustrious Advanced_V37 (TIPO/IPA/OpenPose/Regional)",
        "when": "포즈 고정·얼굴 레퍼·TIPO·리전 프롬프트 등 Standard 이상 풀 키친",
        "when_not": "일상 한 장 → still_anime Standard · 기존컷 후처리만 → still_anime_detailer",
        "keywords": [
            "advanced v37", "tipo", "ipadapter", "openpose", "regional",
            "generate_illustrious_advanced", "illustrious advanced", "noobai advanced",
        ],
        "examples": [
            "python scripts/generate_illustrious_advanced.py --list-features",
            'python scripts/generate_illustrious_advanced.py -p "1girl, solo, ..." -o out.png --seed 42',
            "python scripts/generate_illustrious_advanced.py -p \"...\" --tipo -o out.png",
            "python scripts/generate_illustrious_advanced.py -p \"...\" --openpose pose.png -o out.png",
            "python scripts/generate_illustrious_advanced.py -p \"...\" --ipa face.png -o out.png",
        ],
        "alternatives": [
            {"if": "일상 애니 T2I", "use": "still_anime", "cli": "python scripts/generate_illustrious_standard.py -p \"...\" -o out.png"},
            {"if": "기존 이미지 폴리시", "use": "still_anime_detailer", "cli": "python scripts/generate_illustrious_detailer.py -i still.png -o out.png"},
        ],
    },
    {
        "id": "still_anime_detailer",
        "shelf": "FINISH",
        "cli": "python scripts/generate_illustrious_detailer.py",
        "script": "generate_illustrious_detailer.py",
        "summary": "Illustrious Detailer_V37 (기존 이미지 폴리시·인페·아웃페)",
        "when": "이미 있는 애니 스틸 얼굴/손/눈 정리 · inpaint/outpaint · 워터마크/배경 제거",
        "when_not": "새로 생성 → still_anime · 포즈/IPA 생성 → still_anime_advanced",
        "keywords": [
            "detailer v37", "illustrious detailer", "anime inpaint", "outpaint",
            "generate_illustrious_detailer", "마스크 인페 애니",
        ],
        "examples": [
            "python scripts/generate_illustrious_detailer.py --list-features",
            "python scripts/generate_illustrious_detailer.py --check-models",
            "python scripts/generate_illustrious_detailer.py -i still.png -o polished.png",
            "python scripts/generate_illustrious_detailer.py -i still.png -o out.png --hand --eyes",
            "python scripts/generate_illustrious_detailer.py -i still.png --mask mask.png --inpaint -p \"fix hands\" -o out.png",
            "python scripts/generate_illustrious_detailer.py -i still.png -o out.png --outpaint",
        ],
        "alternatives": [
            {"if": "생성 경로 디테일러", "use": "still_anime", "cli": "python scripts/generate_illustrious_standard.py -p \"...\" --face --hand -o out.png"},
            {"if": "실사 인페", "use": "qwen_inpaint", "cli": "python scripts/generate_qwen_inpaint.py --help"},
        ],
    },
    {
        "id": "still_nsfw",
        "shelf": "GENERATE",
        "cli": "python scripts/generate_krea_nsfw.py",
        "script": "generate_krea_nsfw.py",
        "summary": "성인/언센서 스틸 (18+)",
        "when": "NSFW still",
        "when_not": "SFW 스토리 기본",
        "keywords": ["nsfw", "성인", "18", "krea_nsfw", "언센서", "야한", "uncensored"],
        "examples": [
            'python scripts/generate_krea_nsfw.py -p "adult woman, ..." -o out.png --seed 42',
        ],
        "alternatives": [
            {"if": "SFW 키프레임", "use": "krea SFW", "cli": "python scripts/generate_krea.py -p \"...\" -o out.png"},
            {"if": "NSFW 모션", "use": "ltx_nsfw_i2v", "cli": "python scripts/generate_ltx_nsfw_i2v.py --help"},
        ],
    },
    {
        "id": "typography",
        "shelf": "GENERATE",
        "cli": "python scripts/generate_ideogram4.py",
        "script": "generate_ideogram4.py",
        "summary": "타이틀·간판·잡지 글자",
        "when": "가벼운 타이포 → ideogram · 밀집 포스터 → boogu",
        "when_not": "글자 없는 인물 스틸",
        "keywords": [
            "title", "typo", "text", "font", "간판", "타이틀", "포스터", "잡지",
            "글자", "ideogram", "boogu",
        ],
        "examples": [
            'python scripts/generate_ideogram4.py --slot title_card --text "에피소드 제목" --aspect 9:16 -o title.png',
        ],
        "alternatives": [
            {"if": "밀집 잡지/광고 타이포+인물", "use": "boogu_typo", "cli": "python scripts/generate_boogu_typo.py --mode pipeline -p \"magazine cover, masthead exactly reading TITLE\" -o cover.png"},
            {"if": "글자 없는 인물", "use": "krea SFW", "cli": "python scripts/generate_krea.py -p \"...\" -o out.png"},
        ],
    },
    {
        "id": "identity_scene",
        "shelf": "TRANSFORM",
        "cli": "python scripts/generate_character_consistent.py",
        "script": "generate_character_consistent.py",
        "summary": "같은 사람 유지하며 장면/표정 변경",
        "when": "레퍼 얼굴 있고 장면·행동 바꾸고 ID 유지",
        "when_not": "장기 패키지·부위 마스크",
        "keywords": [
            "identity", "same person", "face lock", "i2i", "일관성", "얼굴 유지",
            "같은 사람", "캐릭터", "아이덴티티", "lock", "remix", "consistent",
        ],
        "examples": [
            'python scripts/generate_character_consistent.py --mode lock -i face.png -p "cafe table, holding cup, soft smile" -o scene.png --seed 42',
        ],
        "alternatives": [
            {"if": "마스크 부위만", "use": "qwen_inpaint", "cli": "python scripts/generate_qwen_inpaint.py -i img.png --mask m.png -p \"blue jacket\" -o out.png"},
            {"if": "매체/그림체 변경", "use": "style_transfer", "cli": "python scripts/generate_style_transfer.py --mode preset --style anime -i face.png -o out.png"},
            {"if": "레퍼 보드 먼저", "use": "ref_pack", "cli": "python scripts/generate_ref_pack.py -i face.png -o pack --profile quick"},
            {"if": "시리즈 SSOT", "use": "character_full_sheet", "cli": "python scripts/character_full_sheet.py --id X --run"},
        ],
    },
    {
        "id": "ref_pack",
        "shelf": "TRANSFORM",
        "cli": "python scripts/generate_ref_pack.py",
        "script": "generate_ref_pack.py",
        "summary": "원샷 레퍼 팩 (패키지 없이 얼굴 보드)",
        "when": "얼굴 1장 → master/표정/각도 보드",
        "when_not": "시리즈 SSOT",
        "keywords": [
            "ref pack", "reference board", "레퍼", "레퍼런스", "원샷", "팩",
            "보드", "contact", "ref_pack",
        ],
        "examples": [
            "python scripts/generate_ref_pack.py -i face.png -o out/pack --profile quick --seed 42",
        ],
        "alternatives": [
            {"if": "한 컷 장면만", "use": "character_consistent", "cli": "python scripts/generate_character_consistent.py --mode lock -i face.png -p \"...\" -o scene.png"},
            {"if": "각도만", "use": "qwen_angle", "cli": "python scripts/generate_qwen_angle.py -i face.png --view head_left_45 -o a.png"},
            {"if": "장기 캐릭", "use": "character package", "cli": "python scripts/character_full_sheet.py --id X --run"},
        ],
    },
    {
        "id": "style_transfer",
        "shelf": "TRANSFORM",
        "cli": "python scripts/generate_style_transfer.py",
        "script": "generate_style_transfer.py",
        "summary": "스타일 전이 / 레스타일",
        "when": "애니·유화·무드보드 스타일, 내용 유지",
        "when_not": "장면만 변경",
        "keywords": [
            "style", "restyle", "anime style", "스타일", "전이", "레스타일",
            "유화", "수채", "만화풍", "style transfer",
        ],
        "examples": [
            "python scripts/generate_style_transfer.py --mode preset --style anime -i photo.png -o out_anime.png --seed 42",
        ],
        "alternatives": [
            {"if": "무드보드 이미지로 스타일", "use": "style_transfer ref", "cli": "python scripts/generate_style_transfer.py --mode ref -i content.png --style-image mood.png -o out.png"},
            {"if": "ID 유지 장면 변경(스타일 동일)", "use": "character_consistent", "cli": "python scripts/generate_character_consistent.py --mode lock -i face.png -p \"...\" -o out.png"},
            {"if": "지시 문장 전체 편집", "use": "qwen_edit", "cli": "python scripts/generate_qwen_edit.py -i img.png -p \"make it watercolor\" -o out.png"},
        ],
    },
    {
        "id": "instruction_edit",
        "shelf": "TRANSFORM",
        "cli": "python scripts/generate_qwen_edit.py",
        "script": "generate_qwen_edit.py",
        "summary": "문장으로 전체 이미지 편집",
        "when": "배경만 밤으로 등 영역 없이 지시",
        "when_not": "마스크 국소",
        "keywords": [
            "edit", "instruction", "배경", "편집", "바꿔", "qwen edit", "문장 편집",
        ],
        "examples": [
            'python scripts/generate_qwen_edit.py -i img.png -p "make the background night city, keep the person" -o out.png',
        ],
        "alternatives": [
            {"if": "마스크 안만", "use": "inpaint", "cli": "python scripts/generate_qwen_inpaint.py -i img.png --mask m.png -p \"...\" -o out.png"},
            {"if": "얼굴 ID + 장면", "use": "character_consistent", "cli": "python scripts/generate_character_consistent.py --mode lock -i face.png -p \"...\" -o out.png"},
            {"if": "그림체 전이", "use": "style_transfer", "cli": "python scripts/generate_style_transfer.py --mode preset --style oil_paint -i img.png -o out.png"},
        ],
    },
    {
        "id": "inpaint",
        "shelf": "TRANSFORM",
        "cli": "python scripts/generate_qwen_inpaint.py",
        "script": "generate_qwen_inpaint.py",
        "summary": "마스크 부위만 수정",
        "when": "옷·손·소품 등 지정 영역",
        "when_not": "마스크 없이 전체",
        "keywords": ["inpaint", "mask", "마스크", "인페", "부위", "국소", "손", "옷"],
        "examples": [
            'python scripts/generate_qwen_inpaint.py -i photo.png --mask torso_mask.png -p "blue denim jacket" -o out.png --gguf-light',
        ],
        "alternatives": [
            {"if": "마스크 없이 전체 지시", "use": "qwen_edit", "cli": "python scripts/generate_qwen_edit.py -i img.png -p \"change jacket to blue\" -o out.png"},
            {"if": "얼굴 전체 ID 리믹스", "use": "character_consistent", "cli": "python scripts/generate_character_consistent.py --mode soft -i face.png -p \"smile\" -o out.png"},
        ],
    },
    {
        "id": "multi_angle",
        "shelf": "CAMERA",
        "cli": "python scripts/generate_qwen_angle.py",
        "script": "generate_qwen_angle.py",
        "summary": "멀티 앵글 / 턴 (앞옆뒤)",
        "when": "동일 인물 방향 전환 시트",
        "when_not": "하이/로우 과장",
        "keywords": [
            "angle", "turnaround", "side view", "각도", "턴", "옆모습", "뒷모습",
            "멀티앵글", "multiangle",
        ],
        "examples": [
            "python scripts/generate_qwen_angle.py -i face.png --view head_left_45 -o left45.png --seed 42",
        ],
        "alternatives": [
            {"if": "하이/로우 앵글 과장", "use": "viewpoint", "cli": "python scripts/generate_viewpoint.py -i still.png --preset low_angle -o out.png"},
            {"if": "크롭만", "use": "reframe", "cli": "python scripts/generate_reframe.py -i key.png -s close_up -o cu.png"},
            {"if": "여러 각도 보드 한 방", "use": "ref_pack full", "cli": "python scripts/generate_ref_pack.py -i face.png -o pack --profile full"},
        ],
    },
    {
        "id": "viewpoint",
        "shelf": "CAMERA",
        "cli": "python scripts/generate_viewpoint.py",
        "script": "generate_viewpoint.py",
        "summary": "깊이·시점 과장 (하이/로우/버즈아이)",
        "when": "카메라 높이·피치·거리 재촬영 느낌",
        "when_not": "크롭·턴테이블",
        "keywords": [
            "high angle", "low angle", "birds eye", "viewpoint", "시점", "하이앵글",
            "로우앵글", "버즈아이", "웜즈아이", "깊이", "카메라 높이",
        ],
        "examples": [
            "python scripts/generate_viewpoint.py -i still.png --preset low_angle -o out_low.png --seed 42 --strength medium",
        ],
        "alternatives": [
            {"if": "앞/옆/뒤 턴만", "use": "qwen_angle", "cli": "python scripts/generate_qwen_angle.py -i face.png --view head_side -o side.png"},
            {"if": "샷 사이즈 크롭", "use": "reframe", "cli": "python scripts/generate_reframe.py -i key.png -s medium_close -o mcu.png"},
            {"if": "영상 속 카메라 무빙", "use": "camera_move", "cli": "python scripts/generate_camera_move.py -i key.png --preset push_in -o clip.mp4"},
        ],
    },
    {
        "id": "reframe",
        "shelf": "CAMERA",
        "cli": "python scripts/generate_reframe.py",
        "script": "generate_reframe.py",
        "summary": "샷 사이즈 리프레임 (크롭, Comfy 없음)",
        "when": "wide/MCU/CU로 자르기",
        "when_not": "카메라 다시 그림",
        "keywords": [
            "reframe", "crop", "close-up", "cu", "mcu", "프레이밍", "리프레임",
            "클로즈업", "크롭", "샷사이즈",
        ],
        "examples": [
            "python scripts/generate_reframe.py -i key.png -s close_up -o key_cu.png --width 1080 --height 1920",
        ],
        "alternatives": [
            {"if": "시점을 다시 생성", "use": "viewpoint", "cli": "python scripts/generate_viewpoint.py -i still.png --preset high_angle -o out.png"},
            {"if": "구도+포즈 구조", "use": "controlnet", "cli": "python scripts/generate_moody_controlnet.py --control pose.png -p \"...\" -o out.png"},
        ],
    },
    {
        "id": "openpose_pose",
        "shelf": "CAMERA",
        "cli": "python scripts/generate_openpose_pose.py",
        "script": "generate_openpose_pose.py",
        "summary": "OpenPose 맵 extract + 템플릿 포즈 생성",
        "when": "걷기/조깅 등 포즈 맵으로 스틸 키 생성 (Fun Union CN 경로)",
        "when_not": "영상 댄스 pose 플레이트 → extract_pose_video · Qwen 텍스트만으로 발 위상 교정 불가",
        "keywords": [
            "openpose", "pose map", "포즈맵", "jog", "walk cycle", "스틱피겨",
            "generate_openpose_pose", "vitpose", "포즈 템플릿", "jogging",
        ],
        "examples": [
            "python scripts/generate_openpose_pose.py generate -i identity.png --template jog_contact -o out.png --seed 42",
            "python scripts/generate_openpose_pose.py extract -i char.png -o pose.png",
            "python scripts/generate_openpose_pose.py list-templates",
        ],
        "alternatives": [
            {"if": "저수준 CN만", "use": "moody_controlnet", "cli": "python scripts/generate_moody_controlnet.py --control pose.png -p \"...\" -o out.png -m pro"},
            {"if": "영상 pose 스틱", "use": "extract_pose_video", "cli": "python scripts/extract_pose_video.py -v dance.mp4 -o pose.mp4 --duration 4"},
            {"if": "얼굴 ID + 포즈 맵", "use": "character_consistent pose", "cli": "python scripts/generate_character_consistent.py --mode pose -i face.png --pose pose.png -o out.png"},
        ],
    },
    {
        "id": "controlnet_pose",
        "shelf": "CAMERA",
        "cli": "python scripts/generate_moody_controlnet.py",
        "script": "generate_moody_controlnet.py",
        "summary": "포즈/구조 ControlNet (저수준)",
        "when": "이미 있는 포즈/캐니 맵으로 몸 구조 고정 (직접 CN)",
        "when_not": "one-stop OpenPose 템플릿 → openpose_pose · 얼굴 ID만",
        "keywords": ["controlnet", "canny", "depth", "구조", "cn", "moody controlnet"],
        "examples": [
            'python scripts/generate_moody_controlnet.py --control pose.png -p "same person standing" -o out.png -m pro',
        ],
        "alternatives": [
            {"if": "OpenPose extract+템플릿", "use": "openpose_pose", "cli": "python scripts/generate_openpose_pose.py generate -i identity.png --template jog_contact -o out.png"},
            {"if": "얼굴 ID 장면 변경", "use": "character_consistent", "cli": "python scripts/generate_character_consistent.py --mode lock -i face.png -p \"standing\" -o out.png"},
            {"if": "댄스 레퍼 영상", "use": "dance_ref", "cli": "python scripts/generate_dance_ref.py -i hero.png -v dance.mp4 -o out.mp4"},
        ],
    },
    {
        "id": "camera_move",
        "shelf": "MOTION",
        "cli": "python scripts/generate_camera_move.py",
        "script": "generate_camera_move.py",
        "summary": "카메라 무빙 의도 I2V",
        "when": "push-in, pan, idle 등 카메라/모션 의도",
        "when_not": "스틸 시점·립",
        "keywords": [
            "camera move", "push in", "dolly", "pan", "orbit", "i2v", "카메라",
            "무빙", "푸시인", "팬", "돌리", "모션",
        ],
        "examples": [
            "python scripts/generate_camera_move.py -i key.png --preset push_in -o clip.mp4 --seed 42",
        ],
        "alternatives": [
            {"if": "대기 루프", "use": "idle_loop", "cli": "python scripts/generate_idle_loop.py -i key.png -o loop.mp4 --mode pingpong"},
            {"if": "자유 모션 문장", "use": "generate_i2v", "cli": "python scripts/generate_i2v.py -i key.png -p \"slow orbit\" -o clip.mp4"},
            {"if": "스틸 하이/로우", "use": "viewpoint", "cli": "python scripts/generate_viewpoint.py -i key.png --preset low_angle -o still.png"},
            {"if": "말하기 립", "use": "s2v", "cli": "python scripts/generate_s2v.py -i face.png -a line.wav -o talk.mp4"},
        ],
    },
    {
        "id": "idle_loop",
        "shelf": "MOTION",
        "cli": "python scripts/generate_idle_loop.py",
        "script": "generate_idle_loop.py",
        "summary": "아이들 모션 + 루프",
        "when": "대기·호흡·핑퐁 루프",
        "when_not": "대사 립",
        "keywords": [
            "idle", "loop", "seamless", "pingpong", "아이들", "루프", "대기",
            "호흡", "반복",
        ],
        "examples": [
            "python scripts/generate_idle_loop.py -i key.png -o idle_loop.mp4 --mode pingpong --seed 42",
        ],
        "alternatives": [
            {"if": "단발 idle만", "use": "camera_move idle", "cli": "python scripts/generate_camera_move.py -i key.png --preset idle -o idle.mp4"},
            {"if": "카메라 푸시인", "use": "camera_move", "cli": "python scripts/generate_camera_move.py -i key.png --preset push_in -o clip.mp4"},
            {"if": "립싱크", "use": "s2v", "cli": "python scripts/generate_s2v.py -i face.png -a line.wav -o talk.mp4"},
        ],
    },
    {
        "id": "dance_ref",
        "shelf": "MOTION",
        "cli": "python scripts/generate_dance_ref.py",
        "script": "generate_dance_ref.py",
        "summary": "댄스/레퍼 모션 리타겟",
        "when": "레퍼 영상처럼 캐릭 움직이기",
        "when_not": "풀 챌린지 에피·립",
        "keywords": [
            "dance", "choreography", "reference motion", "v2v", "댄스", "안무",
            "레퍼 모션", "챌린지", "춤",
        ],
        "examples": [
            "python scripts/generate_dance_ref.py -i hero.png -v dance.mp4 -o out.mp4 --hook-sec 8 --seed 42",
        ],
        "alternatives": [
            {"if": "레퍼 없이 텍스트 댄스", "use": "dance_ref i2v", "cli": "python scripts/generate_dance_ref.py -i hero.png --mode i2v --style kpop -o out.mp4"},
            {"if": "pose 플레이트만 필요", "use": "extract_pose_video", "cli": "python scripts/extract_pose_video.py -v dance.mp4 -o pose.mp4 --duration 4"},
            {"if": "크로스 캐스트·얼굴 유지 댄스", "use": "wan22_animate", "cli": "python scripts/generate_wan22_animate.py -i hero.png -v dance.mp4 -o out.mp4"},
            {"if": "저수준 V2V", "use": "generate_v2v", "cli": "python scripts/generate_v2v.py --intent motion -v dance.mp4 -i hero.png -o out.mp4"},
            {"if": "카메라 의도만", "use": "camera_move", "cli": "python scripts/generate_camera_move.py -i key.png --preset orbit_subtle -o clip.mp4"},
        ],
    },
    {
        "id": "wan22_animate",
        "shelf": "MOTION",
        "cli": "python scripts/generate_wan22_animate.py",
        "script": "generate_wan22_animate.py",
        "summary": "Wan Animate 댄스/모션 리타겟 (얼굴 고정)",
        "when": "RGB 댄스 레퍼를 다른 캐릭에 이식; 크로스 캐스트 아이덴티티 유지",
        "when_not": "립싱크·카메라만·pose 플레이트만",
        "keywords": [
            "animate", "wan animate", "retarget", "choreography", "face strength",
            "애니메이트", "리타겟", "안무 이식", "wan22_animate", "얼굴 고정",
            "크로스 캐스트", "face lock", "dance retarget",
        ],
        "examples": [
            "python scripts/generate_wan22_animate.py -i character.png -v dance.mp4 -o out.mp4 --seed 42",
        ],
        "alternatives": [
            {"if": "빠른 LTX 초안", "use": "dance_ref", "cli": "python scripts/generate_dance_ref.py -i hero.png -v dance.mp4 -o out.mp4"},
            {"if": "pose 맵만", "use": "extract_pose_video", "cli": "python scripts/extract_pose_video.py -v dance.mp4 -i hero.png -o pose.mp4"},
        ],
    },
    {
        "id": "extract_pose_video",
        "shelf": "MOTION",
        "cli": "python scripts/extract_pose_video.py",
        "script": "extract_pose_video.py",
        "summary": "RGB 영상 → pose 스틱 플레이트",
        "when": "댄스/모션 레퍼에서 OpenPose 스타일 제어 영상 뽑기 (Fun Control·Animate 전단계)",
        "when_not": "캐릭 생성·최종 댄스 렌더 자체",
        "keywords": [
            "pose", "openpose", "vitpose", "skeleton", "control video",
            "포즈", "스틱", "제어 맵", "pose extract", "dwpose",
        ],
        "examples": [
            "python scripts/extract_pose_video.py -v dance.mp4 -o pose.mp4 --duration 4 --width 544 --height 960",
        ],
        "alternatives": [
            {"if": "RGB 레퍼로 바로 캐릭 춤", "use": "dance_ref", "cli": "python scripts/generate_dance_ref.py -i hero.png -v dance.mp4 -o out.mp4"},
            {"if": "이미지 한 장 포즈만", "use": "openpose_pose", "cli": "python scripts/generate_openpose_pose.py --help"},
        ],
    },
    {
        "id": "i2v_generic",
        "shelf": "MOTION",
        "cli": "python scripts/generate_i2v.py",
        "script": "generate_i2v.py",
        "summary": "일반 I2V (자유 모션 문장)",
        "when": "키프레임 → 영상, 커스텀 모션 프롬프트",
        "when_not": "의도 id·립",
        "keywords": ["i2v", "image to video", "영상", "모션", "키프레임 애니", "ltx"],
        "examples": [
            'python scripts/generate_i2v.py -i key.png -p "slow push-in, natural motion" -o clip.mp4 --seed 42',
            "python scripts/clip_quality.py recommend --goal work --duration 4",
            'python scripts/clip_quality.py check-prompt -p "slow push-in, soft blink"',
        ],
        "alternatives": [
            {"if": "품질 계획/후처리", "use": "clip_quality", "cli": "python scripts/clip_quality.py recommend --goal hero --face-cu"},
            {"if": "의도 프리셋만", "use": "camera_move", "cli": "python scripts/generate_camera_move.py -i key.png --preset push_in -o clip.mp4"},
            {"if": "첫·끝 프레임", "use": "flf2v", "cli": "python scripts/generate_flf2v.py -i start.png --last end.png -p \"...\" -o bridge.mp4"},
            {"if": "시댄스급+네이티브 오디오", "use": "minimax_h3", "cli": "python scripts/generate_minimax_h3.py --task i2v -i key.png -p \"...\" -o out.mp4"},
            {"if": "오디오 연동", "use": "s2v", "cli": "python scripts/generate_s2v.py -i face.png -a line.wav -o talk.mp4"},
        ],
    },
    {
        "id": "clip_quality",
        "shelf": "MOTION",
        "cli": "python scripts/clip_quality.py",
        "script": "clip_quality.py",
        "summary": "영상 클립 품질 계획·프롬프트 검사·에피 draft→hero·후처리 폴리시",
        "when": "I2V/S2V 전 품질 티어 선택, 에피소드 draft/work/hero 계획, 모션 프롬프트 방언, face/upscale 체인",
        "when_not": "이미 엔진·플래그 확정된 단발 gen",
        "keywords": [
            "clip quality", "video quality", "i2v quality", "motion prompt check",
            "face enhance video", "영상 품질", "클립 품질", "freeze", "blur",
            "draft hero", "episode plan", "2-stage", "hero profile",
        ],
        "examples": [
            "python scripts/clip_quality.py recommend --goal hero --face-cu --duration 3.5",
            'python scripts/clip_quality.py check-prompt -p "slow push-in, soft blink"',
            "python scripts/clip_quality.py episode-plan -e EP --phase full",
            "python scripts/clip_quality.py probe -i clip.mp4",
            "python scripts/clip_quality.py polish -i clip.mp4 -o out.mp4 --goal delivery --face",
            "python scripts/clip_quality.py playbook",
        ],
        "alternatives": [
            {"if": "생성 실행", "use": "i2v_generic", "cli": "python scripts/generate_i2v.py -i key.png -p \"...\" -o clip.mp4 --ltx-profile work"},
            {"if": "에피 배치", "use": "episode_i2v", "cli": "python scripts/episode_i2v.py -e EP --ltx-profile draft"},
            {"if": "업스케일만", "use": "upscale_video", "cli": "python scripts/upscale_recommend.py pick --media video --goal delivery"},
        ],
    },
    {
        "id": "flf2v",
        "shelf": "MOTION",
        "cli": "python scripts/generate_flf2v.py",
        "script": "generate_flf2v.py",
        "summary": "첫·끝 프레임 연결 모션",
        "when": "start/end 스틸 사이 브릿지",
        "when_not": "단일 키프레임",
        "keywords": ["flf", "first last", "start end", "이음", "브릿지", "첫끝"],
        "examples": [
            'python scripts/generate_flf2v.py -i start.png --last end.png -p "continuous natural motion" -o bridge.mp4',
        ],
        "alternatives": [
            {"if": "시작 스틸만", "use": "i2v / camera_move", "cli": "python scripts/generate_camera_move.py -i start.png --preset push_in -o clip.mp4"},
            {"if": "루프로 왕복", "use": "idle_loop roundtrip", "cli": "python scripts/generate_idle_loop.py -i key.png -o loop.mp4 --mode roundtrip"},
        ],
    },
    {
        "id": "s2v_talk",
        "shelf": "MOTION",
        "cli": "python scripts/generate_s2v.py",
        "script": "generate_s2v.py",
        "summary": "이미지+오디오 립/연동",
        "when": "말하기·립싱크·오디오 연동 모션",
        "when_not": "무음 카메라만",
        "keywords": [
            "s2v", "lipsync", "talking", "speech", "립", "말하기", "대사", "토킹",
            "infinitetalk", "si2v",
        ],
        "examples": [
            "python scripts/generate_s2v.py -i face.png -a line.wav -o talk.mp4",
        ],
        "alternatives": [
            {"if": "대사 음성부터", "use": "tts", "cli": "python scripts/generate_qwen3_tts.py --mode custom --speaker Sohee --text \"안녕\" -o line.mp3"},
            {"if": "무음 모션", "use": "camera_move", "cli": "python scripts/generate_camera_move.py -i key.png --preset talk_gesture -o clip.mp4"},
            {"if": "립 품질 최우선", "use": "s2v infinitetalk", "cli": "python scripts/generate_s2v.py --backend infinitetalk -i face.png -a line.wav -o talk.mp4"},
        ],
    },
    {
        "id": "tts",
        "shelf": "VOICE",
        "cli": "python scripts/generate_qwen3_tts.py",
        "script": "generate_qwen3_tts.py",
        "summary": "TTS 대사·클론",
        "when": "음성 생성 / 보이스 클론",
        "when_not": "BGM only",
        "keywords": ["tts", "voice", "clone", "음성", "대사", "보이스", "나레이션"],
        "examples": [
            'python scripts/generate_qwen3_tts.py --mode custom --speaker Sohee --instruct "warm" --text "안녕하세요" -o line.mp3',
        ],
        "alternatives": [
            {"if": "BGM", "use": "generate_bgm", "cli": "python scripts/generate_bgm.py --help"},
            {"if": "립 영상", "use": "s2v after tts", "cli": "python scripts/generate_s2v.py -i face.png -a line.mp3 -o talk.mp4"},
            {"if": "보이스 등록", "use": "voice_register", "cli": "python scripts/voice_register.py --help"},
        ],
    },
    {
        "id": "bgm",
        "shelf": "VOICE",
        "cli": "python scripts/generate_bgm.py",
        "script": "generate_bgm.py",
        "summary": "배경음악",
        "when": "BGM 생성",
        "when_not": "대사 TTS",
        "keywords": ["bgm", "music", "배경음", "음악", "ost"],
        "examples": ["python scripts/generate_bgm.py --help"],
        "alternatives": [
            {"if": "대사 음성", "use": "tts", "cli": "python scripts/generate_qwen3_tts.py --mode custom --speaker Sohee --text \"...\" -o a.mp3"},
        ],
    },
    {
        "id": "youtube_ref_ingest",
        "shelf": "INGEST",
        "cli": "python scripts/youtube_ingest.py",
        "script": "youtube_ingest.py",
        "summary": "유튜브 레퍼 → 메타·자막·요약·하이라이트",
        "when": "참고 유튜브 URL로 쇼츠/에피 기획 전 (내용 파악·구간 클립)",
        "when_not": "이미 로컬 대본·영상 있음 · 원본 재업로드 목적",
        "keywords": [
            "youtube", "유튜브", "transcript", "자막", "레퍼", "ingest",
            "highlight", "하이라이트", "요약", "caption", "yt-dlp", "쇼츠 레퍼",
        ],
        "examples": [
            'python scripts/youtube_ingest.py "https://www.youtube.com/watch?v=VIDEO" -o dumps/yt_demo',
            'python scripts/youtube_ingest.py "URL" --whisper --highlights',
            'python scripts/youtube_ingest.py "URL" --cut --max-clips 5',
            "python scripts/youtube_highlights.py -i dumps/yt_demo --cut",
        ],
        "alternatives": [
            {"if": "자막 없음", "use": "whisper fallback", "cli": "python scripts/youtube_ingest.py URL --whisper"},
            {"if": "패키지 만든 뒤 클립만", "use": "youtube_highlights", "cli": "python scripts/youtube_highlights.py -i dumps/yt_demo --cut"},
            {"if": "우리 쇼츠 자막 납품", "use": "episode_subtitles", "cli": "python scripts/episode_subtitles.py -e EP"},
        ],
    },
    {
        "id": "ltx_i2v",
        "shelf": "MOTION",
        "cli": "python scripts/generate_i2v.py",
        "script": "generate_i2v.py",
        "summary": "LTX 2.3 I2V (기본 work=720p · hero≈1080)",
        "when": "키프레임 → 짧은 모션; 본선 720p, 러프 draft, 히어로 hero",
        "when_not": "립 CU → infinitetalk · 의도 프리셋만 → camera_move",
        "keywords": [
            "ltx", "i2v", "ltx-profile", "hero motion", "영상 생성", "모션",
            "ltx2.3", "image to video", "720p",
        ],
        "examples": [
            'python scripts/generate_i2v.py -i key.png -o out.mp4 -p "slow push in, soft blink"',
            'python scripts/generate_i2v.py -i key.png -o scout.mp4 -p "..." --ltx-profile draft',
            'python scripts/generate_i2v.py -i key.png -o hero.mp4 -p "gentle head turn" --ltx-profile hero --frames 73',
            "python scripts/generate_s2v.py --list-ltx-profiles",
            "python scripts/ltx_lora_status.py   # Asian Face ready? auto-ON on I2V",
        ],
        "alternatives": [
            {"if": "카메라 의도 id만", "use": "camera_move", "cli": "python scripts/generate_camera_move.py -i key.png --preset push_in -o clip.mp4"},
            {"if": "대사 립 히어로", "use": "infinitetalk", "cli": "python scripts/generate_s2v.py --backend infinitetalk -i face.png -a line.wav -o talk.mp4"},
            {"if": "빠른 실험 Wan", "use": "wan22", "cli": "python scripts/generate_i2v.py -i key.png -o out.mp4 -p \"...\" --backend wan22"},
            {"if": "쉬운 Wan MoE T2V/I2V", "use": "yaw_wan22", "cli": "python scripts/generate_yaw_wan22.py --task t2v -p \"...\" -o out.mp4"},
            {"if": "시댄스급 품질+네이티브 오디오", "use": "minimax_h3", "cli": "python scripts/generate_minimax_h3.py -p \"...\" -o out.mp4 --profile work"},
            {"if": "서양인 주연 (Asian Face 끄기)", "use": "ltx no asian face", "cli": "python scripts/generate_s2v.py --no-ltx-asian-face ..."},
            {"if": "야외 클립 재조명", "use": "ltx_relight", "cli": "python scripts/generate_ltx_relight.py -v exterior.mp4 -o relit.mp4 --look \"warm golden low side sun\" --direction \"the left\""},
        ],
    },
    {
        "id": "yaw_wan22",
        "shelf": "MOTION",
        "cli": "python scripts/generate_yaw_wan22.py",
        "script": "generate_yaw_wan22.py",
        "summary": "YAW Wan 2.2 MoE 쉬운 T2V/I2V",
        "when": "Wan MoE 실 UI로 빠른 T2V·I2V 실험 (에피 본선 아님)",
        "when_not": "에피 대량 I2V → LTX · 립 → s2v · 시댄스급+오디오 → minimax_h3",
        "keywords": [
            "yaw", "yaw_wan22", "wan moe", "yet another workflow", "t2v wan",
            "쉬운 wan", "moe t2v",
        ],
        "examples": [
            'python scripts/generate_yaw_wan22.py --task t2v -p "cinematic shot of a woman walking" -o out.mp4',
            "python scripts/generate_yaw_wan22.py --task i2v -i key.png -p \"slow orbit\" -o out.mp4",
        ],
        "alternatives": [
            {"if": "에피 키프레임 모션", "use": "ltx_i2v", "cli": "python scripts/generate_i2v.py -i key.png -p \"...\" -o out.mp4"},
            {"if": "시댄스급+네이티브 오디오", "use": "minimax_h3", "cli": "python scripts/generate_minimax_h3.py -p \"...\" -o out.mp4 --profile work"},
            {"if": "댄스 리타겟", "use": "wan22_animate", "cli": "python scripts/generate_wan22_animate.py -i hero.png -v dance.mp4 -o out.mp4"},
        ],
    },
    {
        "id": "minimax_h3",
        "shelf": "MOTION",
        "cli": "python scripts/generate_minimax_h3.py",
        "script": "generate_minimax_h3.py",
        "summary": "MiniMax H3 T2V/I2V/R2V/A2V + 네이티브 오디오 + polish",
        "when": "시댄스급 품질 쇼츠·텍스트→영상+음향·멀티 레퍼·A2V 립싱크/MV·work 클립 VSR+RIFE 폴리시",
        "when_not": "에피 본선 I2V 대량(LTX) · 프로덕션 토킹헤드 립(s2v/IT) · 초고속 초안만",
        "keywords": [
            "minimax", "minimax h3", "h3", "hailuo", "seedance", "시댄스", "t2v",
            "r2v", "a2v", "audio to video", "lip sync", "native audio", "stereo audio",
            "미니맥스", "영상 오디오", "립싱크", "뮤직비디오", "open weight video",
            "fl2va", "ref2va", "minimax_h3", "polish", "rife", "multiref",
        ],
        "examples": [
            'python scripts/generate_minimax_h3.py -p "Anime cinematic, heroine on cliff at sunset, wind, soft orchestral score" -o out.mp4 --seed 42',
            "python scripts/generate_minimax_h3.py -p \"...\" -o out_native.mp4 --profile native",
            'python scripts/generate_minimax_h3.py --task i2v -i start.png -p "slow push-in, cloak flutters" -o i2v.mp4',
            'python scripts/generate_minimax_h3.py --task r2v --ref-image hero.png --ref-image style.png -p "Use <Picture 1> identity; <Picture 2> style; she walks" -o r2v.mp4',
            'python scripts/generate_minimax_h3.py --task a2v -i face.png -a line.wav -p "[reference generation + audio reference] Use <Picture 1>; lips sync <Audio 1>." -o a2v.mp4 --duration 5',
            "python scripts/generate_minimax_h3.py --task polish -i work.mp4 -o polished.mp4",
            "python scripts/generate_minimax_h3.py --list-profiles",
        ],
        "alternatives": [
            {"if": "에피 키프레임 모션 대량", "use": "ltx_i2v", "cli": "python scripts/generate_i2v.py -i key.png -p \"...\" -o out.mp4"},
            {"if": "빠른 Wan T2V 실험", "use": "yaw_wan22", "cli": "python scripts/generate_yaw_wan22.py --task t2v -p \"...\" -o out.mp4"},
            {"if": "프로덕션 대사 립싱크", "use": "s2v", "cli": "python scripts/generate_s2v.py -i face.png -a line.wav -o talk.mp4"},
            {"if": "생성형 HD 업스케일", "use": "ltx_spatial", "cli": "python scripts/upscale_ltx_spatial.py -i work.mp4 -o hd.mp4 --path full"},
            {"if": "카메라 의도 프리셋만", "use": "camera_move", "cli": "python scripts/generate_camera_move.py -i key.png --preset push_in -o clip.mp4"},
        ],
    },
    {
        "id": "ltx_lora_status",
        "shelf": "META",
        "cli": "python scripts/ltx_lora_status.py",
        "script": "ltx_lora_status.py",
        "summary": "LTX 옵션 LoRA 상태 (Asian Face / Relight)",
        "when": "아시안 얼굴 LoRA·야외 릴라이트 가중치 유무·용도 확인",
        "when_not": "실제 생성 본선 (status만)",
        "keywords": [
            "ltx lora", "asian face", "relight", "아시안", "얼굴 로라", "릴라이트",
            "ltx_lora_status", "east asian", "ic-lora relight", "재조명",
        ],
        "examples": [
            "python scripts/ltx_lora_status.py",
            "python scripts/ltx_lora_status.py --json",
            "python scripts/ltx_lora_status.py show asian_face",
            "python scripts/ltx_lora_status.py download-relight",
        ],
        "alternatives": [
            {"if": "아시안 I2V 생성", "use": "ltx_i2v (asian_face auto)", "cli": "python scripts/generate_i2v.py -i key.png -p \"...\" -o out.mp4"},
            {"if": "야외 재조명", "use": "ltx_relight", "cli": "python scripts/generate_ltx_relight.py -v exterior.mp4 -o relit.mp4 --look \"warm golden low side sun\" --direction \"the left\""},
            {"if": "문서 SSOT", "use": "docs/ltx_loras_agent.md", "cli": "see docs/ltx_loras_agent.md"},
        ],
    },
    {
        "id": "ltx_relight",
        "shelf": "FINISH",
        "cli": "python scripts/generate_ltx_relight.py",
        "script": "generate_ltx_relight.py",
        "summary": "야외 클립 태양 방향·룩 재조명 (LTX IC-LoRA Relight)",
        "when": "완성된 야외 클립 골든아워/측면광/역광 룩 마감 (모션 승인 후)",
        "when_not": "실내·댄스 리타겟·첫 생성·가중치 missing",
        "keywords": [
            "relight", "re-light", "sun direction", "golden hour", "magic hour",
            "재조명", "릴라이트", "야외 조명", "골든아워", "측면광", "역광",
            "ic-lora", "light ball", "ltx relight",
        ],
        "examples": [
            "python scripts/ltx_lora_status.py",
            "python scripts/generate_ltx_relight.py --list-looks",
            'python scripts/generate_ltx_relight.py -v exterior.mp4 -o relit.mp4 --look "warm golden low side sun" --direction "the left" --seed 42',
        ],
        "alternatives": [
            {"if": "가중치 없음", "use": "ltx_lora_status download", "cli": "python scripts/ltx_lora_status.py download-relight"},
            {"if": "얼굴 드리프트", "use": "asian_face / face_stability", "cli": "python scripts/generate_i2v.py -i key.png -p \"...\" -o out.mp4  # asian_face auto"},
            {"if": "해상도만", "use": "upscale_video", "cli": "python scripts/upscale_video.py -i work.mp4 -o deliver.mp4 --preset deliver_1080"},
            {"if": "댄스 아이덴티티", "use": "wan22_animate", "cli": "python scripts/generate_wan22_animate.py -i hero.png -v dance.mp4 -o out.mp4"},
        ],
    },
    {
        "id": "upscale_pick",
        "shelf": "FINISH",
        "cli": "python scripts/upscale_recommend.py",
        "script": "upscale_recommend.py",
        "summary": "업스케일러 선택 (분류·추천, Comfy 없음)",
        "when": "어떤 업스케일 엔진/스타일을 쓸지 모를 때 — 먼저 pick",
        "when_not": "이미 backend 확정 후 실행만",
        "keywords": [
            "upscale", "recommend", "which upscaler", "업스케일", "고해상도", "키우기",
            "4k", "1080", "어떤 업스케일", "업스케일러", "선택", "분류", "backend",
            "esrgan", "seedvr2", "납품 해상도",
        ],
        "examples": [
            "python scripts/upscale_recommend.py --media image --goal delivery --domain photo",
            "python scripts/upscale_recommend.py --media video --goal hero --source blurry",
            "python scripts/upscale_recommend.py matrix",
        ],
        "alternatives": [
            {"if": "스틸 FAST 확정", "use": "upscale_image esrgan", "cli": "python scripts/upscale_image.py -i key.png -o key_1080.png --style photo --preset deliver_1080"},
            {"if": "영상 납품", "use": "upscale_video", "cli": "python scripts/upscale_video.py -i work.mp4 -o deliver.mp4 --preset deliver_1080"},
            {"if": "MiniMax/저해상도 → LTX spatial HD", "use": "ltx_spatial_upscale", "cli": "python scripts/upscale_ltx_spatial.py -i work.mp4 -o out.mp4 --path full"},
            {"if": "히어로 품질", "use": "seedvr2", "cli": "python scripts/upscale_image.py -i key.png -o key_hero.png --backend seedvr2 --preset deliver_1080"},
            {"if": "야외 조명만 변경", "use": "ltx_relight", "cli": "python scripts/generate_ltx_relight.py -v exterior.mp4 -o relit.mp4 --look \"warm golden low side sun\" --direction \"the left\""},
        ],
    },
    {
        "id": "ltx_spatial_upscale",
        "shelf": "FINISH",
        "cli": "python scripts/upscale_ltx_spatial.py",
        "script": "upscale_ltx_spatial.py",
        "summary": "LTX latent spatial x2 (core 빠름 / full IC-LoRA 품질)",
        "when": "MiniMax·저해상도 클립 → LTX spatial HD (오디오 패스스루)",
        "when_not": "일반 납품 ESRGAN/SeedVR2 → upscale_video · 스틸만 → upscale_image",
        "keywords": [
            "ltx spatial", "spatial upscale", "latent upsampler", "minimax upscale",
            "full path", "IC-LoRA upscale", "ltx_spatial", "spatial x2", "latent x2",
        ],
        "examples": [
            "python scripts/upscale_ltx_spatial.py -i work.mp4 -o out.mp4 --path full",
            "python scripts/upscale_ltx_spatial.py -i work.mp4 -o preview.mp4 --path core",
        ],
        "alternatives": [
            {"if": "일반 영상 납품", "use": "upscale_video", "cli": "python scripts/upscale_video.py -i work.mp4 -o deliver.mp4 --preset deliver_1080"},
            {"if": "엔진 모름", "use": "upscale_recommend", "cli": "python scripts/upscale_recommend.py --media video --goal hero --source normal"},
            {"if": "야외 조명만", "use": "ltx_relight", "cli": "python scripts/generate_ltx_relight.py -v exterior.mp4 -o relit.mp4 --look \"warm golden low side sun\" --direction \"the left\""},
        ],
    },
    {
        "id": "upscale",
        "shelf": "FINISH",
        "cli": "python scripts/upscale_image.py",
        "script": "upscale_image.py",
        "summary": "스틸 업스케일 (ESRGAN style / SeedVR2 hero)",
        "when": "키프레임·포스터 1080–4K 납품 (기본 FAST=esrgan+style)",
        "when_not": "해부학 버그 수정 전 · 영상 클립",
        "keywords": [
            "upscale image", "still upscale", "키프레임 업스케일", "스틸 업스케일",
            "photo style", "anime style", "deliver_1080",
        ],
        "examples": [
            "python scripts/upscale_image.py -i key.png -o key_1080.png --style photo --preset deliver_1080",
            "python scripts/upscale_image.py -i anime.png -o a_1080.png --style anime --preset deliver_1080",
            "python scripts/upscale_image.py -i key.png -o key_hero.png --backend seedvr2 --preset deliver_1080",
        ],
        "alternatives": [
            {"if": "어떤 엔진?", "use": "upscale_recommend", "cli": "python scripts/upscale_recommend.py --media image --goal delivery --domain photo"},
            {"if": "구조/얼굴 깨짐", "use": "edit first", "cli": "python scripts/generate_qwen_edit.py -i img.png -p \"fix hands\" -o fixed.png"},
            {"if": "영상 업스케일", "use": "upscale_video", "cli": "python scripts/upscale_video.py -i work.mp4 -o deliver.mp4 --preset deliver_1080"},
            {"if": "4K 마스터", "use": "seedvr2_max", "cli": "python scripts/upscale_image.py -i key.png -o key_4k.png --backend seedvr2_max --preset deliver_2160"},
        ],
    },
    {
        "id": "upscale_video",
        "shelf": "FINISH",
        "cli": "python scripts/upscale_video.py",
        "script": "upscale_video.py",
        "summary": "영상 클립 업스케일 납품",
        "when": "I2V work 클립 → deliver_1080/2160 (기본 esrgan, 히어로 seedvr2)",
        "when_not": "얼굴 스미어만 · 스틸 단독 · MiniMax→LTX spatial은 ltx_spatial_upscale",
        "keywords": [
            "upscale video", "video upscale", "영상 업스케일", "클립 업스케일",
            "deliver video", "work to 1080", "4k video",
        ],
        "examples": [
            "python scripts/upscale_video.py -i work.mp4 -o deliver.mp4 --preset deliver_1080",
            "python scripts/upscale_video.py -i work.mp4 -o deliver_hero.mp4 --backend seedvr2 --preset deliver_1080",
            "python scripts/upscale_video.py -i work.mp4 -o deliver_4k.mp4 --backend seedvr2 --preset deliver_2160 --two-pass",
        ],
        "alternatives": [
            {"if": "어떤 엔진?", "use": "upscale_recommend", "cli": "python scripts/upscale_recommend.py --media video --goal delivery --source normal"},
            {"if": "MiniMax/저해상도 LTX spatial", "use": "ltx_spatial_upscale", "cli": "python scripts/upscale_ltx_spatial.py -i work.mp4 -o out.mp4 --path full"},
            {"if": "I2V 후 얼굴만 깨짐", "use": "wan22_face_enhance", "cli": "python scripts/generate_wan22_face_enhance.py -i work.mp4 -o face_fixed.mp4"},
            {"if": "스틸만", "use": "upscale_image", "cli": "python scripts/upscale_image.py -i key.png -o key_1080.png --style photo --preset deliver_1080"},
        ],
    },
    {
        "id": "upscale_hero",
        "shelf": "FINISH",
        "cli": "python scripts/upscale_image.py --backend seedvr2",
        "script": "upscale_image.py",
        "summary": "히어로 품질 업스케일 (SeedVR2)",
        "when": "최종 마스터·블러 복원·포스터 1컷 (느림, opt-in)",
        "when_not": "에피소드 전 샷 배치 기본 경로",
        "keywords": [
            "seedvr2", "hero upscale", "히어로 업스케일", "복원", "master", "4k master",
            "blurry restore", "최대 품질",
        ],
        "examples": [
            "python scripts/upscale_image.py -i key.png -o key_hero.png --backend seedvr2 --preset deliver_1080",
            "python scripts/upscale_video.py -i work.mp4 -o hero.mp4 --backend seedvr2 --preset deliver_1080",
            "python scripts/upscale_image.py -i key.png -o key_4k.png --backend seedvr2_max --preset deliver_2160",
        ],
        "alternatives": [
            {"if": "배치/시간 부족", "use": "esrgan FAST", "cli": "python scripts/upscale_image.py -i key.png -o key_1080.png --style photo --preset deliver_1080"},
            {"if": "선택 도우미", "use": "upscale_recommend", "cli": "python scripts/upscale_recommend.py --media image --goal hero --source blurry"},
        ],
    },
    {
        "id": "character_package",
        "shelf": "ASSETS",
        "cli": "python scripts/character_full_sheet.py",
        "script": "character_full_sheet.py",
        "summary": "장기 캐릭 패키지/시트 (옵션)",
        "when": "시리즈·다에피 동일 인물 SSOT",
        "when_not": "원샷",
        "keywords": [
            "character package", "full sheet", "cast", "캐릭 패키지", "시트",
            "턴어라운드", "의상", "promote",
        ],
        "examples": [
            "python scripts/character_full_sheet.py --id my_char_v1 --run",
        ],
        "alternatives": [
            {"if": "원샷 보드만", "use": "ref_pack", "cli": "python scripts/generate_ref_pack.py -i face.png -o pack --profile quick"},
            {"if": "한 장면 ID", "use": "character_consistent", "cli": "python scripts/generate_character_consistent.py --mode lock -i face.png -p \"...\" -o out.png"},
        ],
    },
    {
        "id": "episode_bundle",
        "shelf": "BUNDLE",
        "cli": "python scripts/story_init.py",
        "script": "story_init.py",
        "summary": "에피소드 패키지·배치·합본 (옵션)",
        "when": "stories/ 레일, 멀티샷 승인 게이트",
        "when_not": "단일 클립만",
        "keywords": [
            "episode", "assemble", "story", "에피소드", "합본", "샷", "approve",
            "story_init", "배치",
        ],
        "examples": [
            "python scripts/story_init.py --help",
            "python scripts/episode_i2v.py -e MY_EP --motion-preset push_in",
            "python scripts/assemble_video.py -e MY_EP --stage work",
        ],
        "alternatives": [
            {"if": "클립 하나만", "use": "camera_move / i2v", "cli": "python scripts/generate_camera_move.py -i key.png --preset push_in -o clip.mp4"},
            {"if": "의도 검색", "use": "tool_intent", "cli": "python scripts/tool_intent.py \"키프레임 영상\""},
        ],
    },
    {
        "id": "hy3d_mesh",
        "shelf": "MESH",
        "cli": "python scripts/generate_hy3d_mesh.py",
        "script": "generate_hy3d_mesh.py",
        "summary": "2D 이미지 → 3D 메쉬 GLB (Hunyuan3D / Hy3D)",
        "when": "프론트 스틸에서 캐릭/메카/프롭 메쉬 생성 (기본 work 프로필)",
        "when_not": "영상 I2V · 2D 스틸만 · 프로덕션 Warudo 본 리그 (수동 QA 필요)",
        "keywords": [
            "3d", "mesh", "glb", "hunyuan", "hunyuan3d", "hy3d", "메쉬", "3d 모델",
            "image to 3d", "이미지 3d", "generate_hy3d_mesh", "오브젝트 메쉬",
        ],
        "examples": [
            "python scripts/generate_hy3d_mesh.py -i front.png -o out.glb --seed 42",
            "python scripts/generate_hy3d_mesh.py -i front.png -o scout.glb --profile draft",
            "python scripts/generate_hy3d_mesh.py -i front.png -o tex.glb --profile hero --texture",
            "python scripts/generate_hy3d_mesh.py --list-profiles",
        ],
        "alternatives": [
            {"if": "프론트 스틸이 약함", "use": "krea / character_consistent", "cli": "python scripts/generate_krea.py -p \"front view character...\" -o front.png"},
            {"if": "메쉬 정리·라이트 리그", "use": "process_mesh_glb", "cli": "python scripts/process_mesh_glb.py -i out.glb -o clean.glb"},
            {"if": "VRM 프로토타입", "use": "export_mesh_vrm", "cli": "python scripts/export_mesh_vrm.py -i clean.glb -o avatar.vrm"},
        ],
    },
    {
        "id": "process_mesh_glb",
        "shelf": "MESH",
        "cli": "python scripts/process_mesh_glb.py",
        "script": "process_mesh_glb.py",
        "summary": "GLB 클린 / 라이트 auto-rig (Blender MCP)",
        "when": "Hy3D raw GLB 정리·프로토타입 아마추어 부착",
        "when_not": "Blender MCP 없음 · 프로덕션 휴머노이드 본 맵",
        "keywords": [
            "mesh clean", "auto rig", "glb clean", "blender mcp", "메쉬 정리",
            "리그", "process_mesh_glb", "floaters",
        ],
        "examples": [
            "python scripts/process_mesh_glb.py -i raw.glb -o clean.glb",
            "python scripts/process_mesh_glb.py -i raw.glb -o rigged.glb --auto-rig",
            "python scripts/process_mesh_glb.py --probe",
        ],
        "alternatives": [
            {"if": "메쉬 생성부터", "use": "hy3d_mesh", "cli": "python scripts/generate_hy3d_mesh.py -i front.png -o out.glb"},
            {"if": "VRM 내보내기", "use": "export_mesh_vrm", "cli": "python scripts/export_mesh_vrm.py -i clean.glb -o avatar.vrm"},
            {"if": "Blender 오프라인", "use": "probe", "cli": "python scripts/process_mesh_glb.py --probe"},
        ],
    },
    {
        "id": "export_mesh_vrm",
        "shelf": "MESH",
        "cli": "python scripts/export_mesh_vrm.py",
        "script": "export_mesh_vrm.py",
        "summary": "GLB/blend → VRM (Blender MCP + VRM addon)",
        "when": "프로토타입 VTuber/Warudo용 VRM 내보내기",
        "when_not": "프로덕션 본 매핑·스킨 품질 보증 필요 시 (수동 Blender)",
        "keywords": [
            "vrm", "warudo", "vtuber", "export vrm", "브이알엠", "워루도",
            "export_mesh_vrm", "아바타",
        ],
        "examples": [
            "python scripts/export_mesh_vrm.py -i clean.glb -o avatar.vrm",
            "python scripts/export_mesh_vrm.py -i clean.glb -o avatar.vrm --no-auto-rig",
            "python scripts/export_mesh_vrm.py --probe",
        ],
        "alternatives": [
            {"if": "메쉬 없음", "use": "hy3d_mesh", "cli": "python scripts/generate_hy3d_mesh.py -i front.png -o out.glb"},
            {"if": "먼저 클린", "use": "process_mesh_glb", "cli": "python scripts/process_mesh_glb.py -i out.glb -o clean.glb"},
            {"if": "Blender/VRM addon 없음", "use": "probe", "cli": "python scripts/export_mesh_vrm.py --probe"},
        ],
    },
    {
        "id": "failure_notes",
        "shelf": "META",
        "cli": "python scripts/failure_note.py",
        "script": "failure_note.py",
        "summary": "실패 노트 검색·기록 (실수 방지)",
        "when": "생성 전 교훈 검색 · FAIL 후 add",
        "when_not": "순수 도구 선택만 → tool_intent",
        "keywords": [
            "failure", "mistake", "prevent", "freeze", "feet", "framing",
            "실패", "실수", "방지", "교훈", "failure_note", "QA FAIL", "리젝",
        ],
        "examples": [
            'python scripts/failure_note.py before "freeze OR feet OR framing"',
            'python scripts/failure_note.py search "anatomy_feet"',
            "python scripts/failure_note.py list --limit 10",
        ],
        "alternatives": [
            {"if": "어떤 생성 도구인지 모름", "use": "tool_intent", "cli": "python scripts/tool_intent.py \"얼굴 유지\""},
            {"if": "카드 표준", "use": "toolbox_card_standard", "cli": "see docs/toolbox_card_standard.md"},
        ],
    },
]


def _tokenize(q: str) -> list[str]:
    q = (q or "").strip().lower()
    if not q:
        return []
    parts = re.findall(r"[a-z0-9_]+|[가-힣]+", q)
    return [p for p in parts if len(p) >= 1]


_PHRASE_BOOSTS: list[tuple[tuple[str, ...], str, float]] = [
    (("얼굴", "유지"), "identity_scene", 6.0),
    (("같은", "사람"), "identity_scene", 6.0),
    (("아이덴티티",), "identity_scene", 4.0),
    (("same", "person"), "identity_scene", 5.0),
    (("face", "lock"), "identity_scene", 5.0),
    (("푸시",), "camera_move", 4.0),
    (("push", "in"), "camera_move", 5.0),
    # "시댄스" contains "댄스" — handled separately for minimax_h3; avoid false boost
    (("댄스", "레퍼"), "dance_ref", 5.0),
    (("댄스", "안무"), "dance_ref", 5.0),
    (("dance",), "dance_ref", 4.0),
    (("시댄스",), "minimax_h3", 8.0),
    (("seedance",), "minimax_h3", 7.0),
    (("minimax",), "minimax_h3", 6.0),
    (("hailuo",), "minimax_h3", 5.0),
    (("미니맥스",), "minimax_h3", 6.0),
    (("포즈", "추출"), "extract_pose_video", 6.0),
    (("pose", "extract"), "extract_pose_video", 6.0),
    (("openpose",), "openpose_pose", 6.0),
    (("포즈맵",), "openpose_pose", 5.0),
    (("pose", "map"), "openpose_pose", 5.0),
    (("vitpose", "video"), "extract_pose_video", 5.0),
    (("애니메이트",), "wan22_animate", 5.0),
    (("wan", "animate"), "wan22_animate", 6.0),
    (("리타겟",), "wan22_animate", 4.0),
    (("댄스", "얼굴"), "wan22_animate", 7.0),
    (("얼굴", "고정"), "wan22_animate", 5.0),
    (("face", "lock", "dance"), "wan22_animate", 7.0),
    (("크로스", "캐스트"), "wan22_animate", 6.0),
    (("yaw",), "yaw_wan22", 7.0),
    (("wan", "moe"), "yaw_wan22", 6.0),
    (("루프",), "idle_loop", 4.0),
    (("아이들",), "idle_loop", 4.0),
    (("스타일", "전이"), "style_transfer", 6.0),
    (("style", "transfer"), "style_transfer", 5.0),
    (("레퍼", "팩"), "ref_pack", 5.0),
    (("하이앵글",), "viewpoint", 5.0),
    (("로우앵글",), "viewpoint", 5.0),
    (("립",), "s2v_talk", 4.0),
    (("lipsync",), "s2v_talk", 4.0),
    (("유튜브",), "youtube_ref_ingest", 5.0),
    (("youtube",), "youtube_ref_ingest", 4.0),
    (("자막", "추출"), "youtube_ref_ingest", 5.0),
    (("업스케일",), "upscale_pick", 4.0),
    (("upscale",), "upscale_pick", 3.0),
    (("어떤", "업스케일"), "upscale_pick", 6.0),
    (("which", "upscale"), "upscale_pick", 5.0),
    (("spatial", "upscale"), "ltx_spatial_upscale", 8.0),
    (("ltx", "spatial"), "ltx_spatial_upscale", 8.0),
    (("latent", "upsampler"), "ltx_spatial_upscale", 6.0),
    (("seedvr",), "upscale_hero", 5.0),
    (("히어로", "업스케일"), "upscale_hero", 5.0),
    (("영상", "업스케일"), "upscale_video", 5.0),
    (("video", "upscale"), "upscale_video", 5.0),
    (("clip", "quality"), "clip_quality", 8.0),
    (("video", "quality"), "clip_quality", 7.0),
    (("영상", "품질"), "clip_quality", 7.0),
    (("motion", "prompt"), "clip_quality", 5.0),
    (("i2v", "quality"), "clip_quality", 6.0),
    (("episode", "draft"), "clip_quality", 6.0),
    (("draft", "hero"), "clip_quality", 7.0),
    (("episode-plan",), "clip_quality", 8.0),
    (("2-stage",), "clip_quality", 5.0),
    (("재조명",), "ltx_relight", 6.0),
    (("릴라이트",), "ltx_relight", 6.0),
    (("relight",), "ltx_relight", 5.0),
    (("골든아워",), "ltx_relight", 5.0),
    (("golden", "hour"), "ltx_relight", 5.0),
    (("아시안", "얼굴"), "ltx_lora_status", 5.0),
    (("asian", "face"), "ltx_lora_status", 5.0),
    (("krea",), "still_photoreal", 4.0),
    (("krea2",), "still_photoreal", 6.0),
    (("illustrious", "advanced"), "still_anime_advanced", 8.0),
    (("tipo",), "still_anime_advanced", 7.0),
    (("openpose", "illustrious"), "still_anime_advanced", 7.0),
    (("ipadapter", "anime"), "still_anime_advanced", 7.0),
    (("illustrious", "detailer"), "still_anime_detailer", 8.0),
    (("anime", "inpaint"), "still_anime_detailer", 6.0),
    (("anime", "outpaint"), "still_anime_detailer", 6.0),
    (("lonecat", "krea"), "krea2_features", 7.0),
    (("krea", "v7"), "krea2_features", 8.0),
    (("moodboard",), "krea2_features", 6.0),
    (("krea", "feature"), "krea2_features", 7.0),
    (("krea", "bypass"), "krea2_features", 6.0),
    (("krea", "style"), "krea2_style", 7.0),
    (("style", "reference"), "krea2_style", 5.0),
    (("krea", "control"), "krea2_control", 7.0),
    (("depth", "control"), "krea2_control", 6.0),
    (("control", "lora"), "krea2_control", 6.0),
    (("img", "prompt"), "krea2_img_prompt", 7.0),
    (("image", "to", "prompt"), "krea2_img_prompt", 7.0),
    (("florence",), "krea2_img_prompt", 6.0),
    (("캡션",), "krea2_img_prompt", 5.0),
    (("face", "detail"), "krea2_face_detail", 7.0),
    (("얼굴", "보정"), "krea2_face_detail", 6.0),
    (("facedetailer",), "krea2_face_detail", 7.0),
    (("dual", "style"), "krea2_style", 6.0),
    (("hand", "detail"), "krea2_hand_detail", 7.0),
    (("손", "보정"), "krea2_hand_detail", 6.0),
    (("moodboard",), "krea2_moodboard", 7.0),
    (("무드보드",), "krea2_moodboard", 7.0),
    (("rmbg",), "rmbg", 7.0),
    (("배경", "제거"), "rmbg", 7.0),
    (("remove", "background"), "rmbg", 6.0),
    (("cutout",), "rmbg", 5.0),
    (("post", "polish"), "krea2_post", 7.0),
    (("film", "grain"), "krea2_post", 6.0),
    (("그레인",), "krea2_post", 5.0),
    (("샤픈",), "krea2_post", 5.0),
    (("color", "match"), "krea2_color_match", 7.0),
    (("colormatch",), "krea2_color_match", 8.0),
    (("컬러매치",), "krea2_color_match", 7.0),
    (("색", "보정"), "krea2_color_match", 5.0),
    (("draft",), "krea_draft", 5.0),
    (("scout",), "krea_draft", 5.0),
    (("드래프트",), "krea_draft", 6.0),
    (("anatomy", "detail"), "krea2_anatomy_detail", 7.0),
    (("nsfw", "detailer"), "krea2_region_detail", 6.0),
    (("eyes", "detail"), "krea2_eyes_detail", 7.0),
    (("눈", "보정"), "krea2_eyes_detail", 6.0),
    (("eye", "detailer"), "krea2_eyes_detail", 7.0),
    (("region", "detail"), "krea2_region_detail", 7.0),
    (("spare", "detail"), "krea2_region_detail", 6.0),
    (("breasts", "detail"), "krea2_region_detail", 7.0),
    (("female", "body"), "krea2_region_detail", 6.0),
    (("male", "junk"), "krea2_region_detail", 6.0),
    (("vajayjay",), "krea2_region_detail", 8.0),
    (("실사", "한장"), "still_photoreal", 5.0),
    (("실사", "한", "장"), "still_photoreal", 5.0),
    (("3d",), "hy3d_mesh", 6.0),
    (("메쉬",), "hy3d_mesh", 6.0),
    (("glb",), "hy3d_mesh", 5.0),
    (("hunyuan",), "hy3d_mesh", 7.0),
    (("hunyuan3d",), "hy3d_mesh", 8.0),
    (("hy3d",), "hy3d_mesh", 7.0),
    (("이미지", "3d"), "hy3d_mesh", 7.0),
    (("image", "to", "3d"), "hy3d_mesh", 7.0),
    (("vrm",), "export_mesh_vrm", 7.0),
    (("warudo",), "export_mesh_vrm", 6.0),
    (("워루도",), "export_mesh_vrm", 6.0),
    (("메쉬", "정리"), "process_mesh_glb", 6.0),
    (("auto", "rig"), "process_mesh_glb", 5.0),
]


def search_intents(
    query: str,
    *,
    shelf: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    tokens = _tokenize(query)
    qraw = (query or "").strip().lower()
    if not tokens and not qraw:
        return []

    scored: list[tuple[float, dict[str, Any]]] = []
    shelf_f = (shelf or "").strip().upper() or None

    for tool in INTENT_TOOLS:
        if shelf_f and str(tool.get("shelf", "")).upper() != shelf_f:
            continue
        score = 0.0
        tid = str(tool.get("id", ""))
        kws = [str(k).lower() for k in (tool.get("keywords") or [])]
        blob = " ".join(
            [
                tid,
                str(tool.get("summary", "")),
                str(tool.get("when", "")),
                str(tool.get("cli", "")),
                " ".join(kws),
            ]
        ).lower()

        for t in tokens:
            if t in kws:
                score += 3.0
            elif any(t in k or k in t for k in kws if len(t) >= 2):
                score += 1.5
            if t in blob:
                score += 0.8
            if t == tid.lower():
                score += 5.0
            if t in str(tool.get("script", "")).lower():
                score += 2.0

        if qraw and len(qraw) >= 2 and qraw in blob:
            score += 2.5

        for parts, boost_id, bonus in _PHRASE_BOOSTS:
            if tid == boost_id and all(p.lower() in qraw for p in parts):
                score += bonus

        if tid == "instruction_edit" and "유지" in qraw and "얼굴" in qraw:
            score -= 2.0

        if score > 0:
            row = dict(tool)
            row["score"] = round(score, 2)
            scored.append((score, row))

    scored.sort(key=lambda x: (-x[0], x[1].get("id", "")))
    return [r for _, r in scored[: max(1, int(limit))]]


def list_by_shelf(shelf: str | None = None) -> list[dict[str, Any]]:
    if not shelf:
        return list(INTENT_TOOLS)
    s = shelf.strip().upper()
    return [t for t in INTENT_TOOLS if str(t.get("shelf", "")).upper() == s]


def list_shelves() -> list[str]:
    seen: list[str] = []
    for t in INTENT_TOOLS:
        sh = str(t.get("shelf", ""))
        if sh and sh not in seen:
            seen.append(sh)
    return seen


def format_match(tool: dict[str, Any], *, verbose: bool = True) -> str:
    """Human card: one-line example + failure alternatives."""
    lines = [
        f"[{tool.get('shelf')}] {tool.get('id')}  score={tool.get('score', '-')}",
        f"  {tool.get('summary')}",
        f"  when: {tool.get('when')}",
    ]
    ex = tool.get("examples") or []
    if ex:
        lines.append(f"  eg:   {ex[0]}")
        if verbose and len(ex) > 1:
            for e in ex[1:3]:
                lines.append(f"       {e}")
    else:
        lines.append(f"  CLI:  {tool.get('cli')}")

    alts = tool.get("alternatives") or []
    if verbose and alts:
        lines.append("  if fail / wrong tool → try:")
        for a in alts[:4]:
            if isinstance(a, dict):
                lines.append(
                    f"    · {a.get('if')}: {a.get('use')}"
                )
                if a.get("cli"):
                    lines.append(f"      {a.get('cli')}")
            else:
                lines.append(f"    · {a}")
    elif verbose and tool.get("when_not"):
        lines.append(f"  not:  {tool.get('when_not')}")
    return "\n".join(lines)
