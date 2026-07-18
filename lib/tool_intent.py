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
        "cli": "python scripts/generate_moody.py",
        "script": "generate_moody.py",
        "summary": "실사 시네 스틸 T2I",
        "when": "텍스트만으로 인물/무드 한 장",
        "when_not": "애니·NSFW·ID 유지 변형",
        "keywords": [
            "t2i", "still", "photo", "photoreal", "portrait", "무드", "실사", "스틸",
            "키프레임", "생성", "한장", "lonecat", "moody",
        ],
        "examples": [
            'python scripts/generate_moody.py -m pro -p "cinematic portrait of a woman" '
            "-o out.png --seed 42",
        ],
        "alternatives": [
            {"if": "애니/일루스 태그", "use": "Illustrious XL", "cli": "python scripts/generate_illustrious_standard.py -p \"1girl, ...\" -o out.png"},
            {"if": "18+ NSFW", "use": "Krea NSFW", "cli": "python scripts/generate_krea_nsfw.py -p \"...\" -o out.png"},
            {"if": "레퍼 얼굴 유지하며 장면만 변경", "use": "character_consistent", "cli": "python scripts/generate_character_consistent.py --mode lock -i face.png -p \"...\" -o out.png"},
        ],
    },
    {
        "id": "still_anime",
        "shelf": "GENERATE",
        "cli": "python scripts/generate_illustrious_standard.py",
        "script": "generate_illustrious_standard.py",
        "summary": "애니/일루스 XL 스틸",
        "when": "Danbooru 태그·일러 체크포인트 스틸",
        "when_not": "실사 photoreal",
        "keywords": ["anime", "illustrious", "애니", "일러", "만화", "xl", "태그"],
        "examples": [
            'python scripts/generate_illustrious_standard.py -p "masterpiece, best quality, 1girl, solo, portrait" -o out.png --seed 42',
        ],
        "alternatives": [
            {"if": "실사 인물", "use": "moody T2I", "cli": "python scripts/generate_moody.py -m pro -p \"...\" -o out.png"},
            {"if": "사진→애니 레스타일", "use": "style_transfer", "cli": "python scripts/generate_style_transfer.py --mode preset --style anime -i photo.png -o out.png"},
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
        "keywords": ["nsfw", "성인", "18", "krea", "언센서", "야한"],
        "examples": [
            'python scripts/generate_krea_nsfw.py -p "adult woman, ..." -o out.png --seed 42',
        ],
        "alternatives": [
            {"if": "SFW 키프레임", "use": "moody", "cli": "python scripts/generate_moody.py -m pro -p \"...\" -o out.png"},
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
            {"if": "글자 없는 인물", "use": "moody", "cli": "python scripts/generate_moody.py -p \"...\" -o out.png"},
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
        "id": "controlnet_pose",
        "shelf": "CAMERA",
        "cli": "python scripts/generate_moody_controlnet.py",
        "script": "generate_moody_controlnet.py",
        "summary": "포즈/구조 ControlNet",
        "when": "포즈 맵·캐니로 몸 구조 고정",
        "when_not": "얼굴 ID만",
        "keywords": ["controlnet", "pose", "openpose", "포즈", "구조", "스틱"],
        "examples": [
            'python scripts/generate_moody_controlnet.py --control pose.png -p "same person standing" -o out.png -m pro',
        ],
        "alternatives": [
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
            {"if": "저수준 V2V", "use": "generate_v2v", "cli": "python scripts/generate_v2v.py --intent motion -v dance.mp4 -i hero.png -o out.mp4"},
            {"if": "카메라 의도만", "use": "camera_move", "cli": "python scripts/generate_camera_move.py -i key.png --preset orbit_subtle -o clip.mp4"},
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
        ],
        "alternatives": [
            {"if": "의도 프리셋만", "use": "camera_move", "cli": "python scripts/generate_camera_move.py -i key.png --preset push_in -o clip.mp4"},
            {"if": "첫·끝 프레임", "use": "flf2v", "cli": "python scripts/generate_flf2v.py -i start.png --last end.png -p \"...\" -o bridge.mp4"},
            {"if": "오디오 연동", "use": "s2v", "cli": "python scripts/generate_s2v.py -i face.png -a line.wav -o talk.mp4"},
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
        ],
        "alternatives": [
            {"if": "카메라 의도 id만", "use": "camera_move", "cli": "python scripts/generate_camera_move.py -i key.png --preset push_in -o clip.mp4"},
            {"if": "대사 립 히어로", "use": "infinitetalk", "cli": "python scripts/generate_s2v.py --backend infinitetalk -i face.png -a line.wav -o talk.mp4"},
            {"if": "빠른 실험 Wan", "use": "wan22", "cli": "python scripts/generate_i2v.py -i key.png -o out.mp4 -p \"...\" --backend wan22"},
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
            {"if": "히어로 품질", "use": "seedvr2", "cli": "python scripts/upscale_image.py -i key.png -o key_hero.png --backend seedvr2 --preset deliver_1080"},
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
        "when_not": "얼굴 스미어만 · 스틸 단독",
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
    (("댄스",), "dance_ref", 5.0),
    (("dance",), "dance_ref", 4.0),
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
    (("seedvr",), "upscale_hero", 5.0),
    (("히어로", "업스케일"), "upscale_hero", 5.0),
    (("영상", "업스케일"), "upscale_video", 5.0),
    (("video", "upscale"), "upscale_video", 5.0),
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
