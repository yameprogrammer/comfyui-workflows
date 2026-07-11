# 📦 에피소드 납품 패키징 (에이전트 → 사용자)

- **작성일**: 2026-07-11  
- **목적**: 수주한 에피소드 결과물을 **한 폴더(+zip)** 로 묶어 사용자에게 전달  
- **CLI**: `scripts/package_delivery.py`

---

## 1. 에이전트 입장에서의 원칙

| 구분 | 위치 | 왜 |
|------|------|-----|
| **작업 중 (작업실)** | `stories/<episode_id>/` | 샷 단위 재생성·승인·I2V에 최적 |
| **공유 자산** | `characters/`, `locations/`, `looks/` | 여러 에피소드 재사용 (납품 zip에 전부 넣지 않음) |
| **사용자 전달 (상자)** | **`deliveries/<episode>__<UTC>/`** | 열어보기 쉬운 스냅샷 + zip |

에이전트는 작업실에서 만들고, **넘길 때만** `package_delivery` 로 상자를 만든다.

---

## 2. 납품 패키지 레이아웃

```text
deliveries/
  mina_cafe_ep01__20260711_153045/
    README.md                 ← 사용자용 안내
    FINAL/
      mina_cafe_ep01_final.mp4
    STILLS/
      S01.png
      S02.png
      ...
    CLIPS/
      S01.mp4                 ← deliver 우선, 없으면 work
      S02.mp4
    MANIFEST/
      shots.json              ← 에피소드 SSOT 복사
      delivery_manifest.json  ← 해시·포함 목록·엔진 메모
      asset_refs.json         ← char/loc/look id만 (풀 팩 아님)
    META/                     ← 선택: 생성 메타 JSON
  mina_cafe_ep01__20260711_153045.zip
```

---

## 3. CLI

```bash
# 미리보기
python scripts/package_delivery.py --episode mina_cafe_ep01 --dry-run

# 폴더 + zip 생성 (기본)
python scripts/package_delivery.py --episode mina_cafe_ep01

# deliver 클립만 / zip 없이
python scripts/package_delivery.py --episode mina_cafe_ep01 --stage deliver --no-zip
```

권장 납품 직전 순서:

```text
episode_i2v → episode_upscale → assemble_video → package_delivery
```

`FINAL/` 이 비어 있으면 사용자에게 “클립·스틸만 포함, 조립본 없음”이라고 README에 표시된다.  
가능하면 `assemble_video` 후 패키징.

---

## 4. 사용자에게 뭐를 주면 되나

1. **`deliveries/<name>.zip`** 하나 (또는 폴더)  
2. (선택) 재작업 요청 시 에이전트에게 `episode_id` + `package_name` 전달  

전체 `characters/` 복사본은 **기본 납품에 넣지 않는다** (용량·라이선스·재사용 구조).  
필요 시 별도 “에셋 덤프” 요청.

---

## 5. 작업실 vs 상자

```text
stories/ep/          ← 계속 작업·재생성 (에이전트 작업실)
deliveries/ep__ts/   ← 그 시점 스냅샷 (사용자 상자)
```

같은 에피소드를 여러 번 납품하면 **타임스탬프별 패키지**가 쌓인다.  
`shots.json` 의 `last_delivery` 에 최근 패키지 경로가 기록된다.
