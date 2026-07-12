# Cast brief — sonagi_heroine_cast_v2

- **cast_id**: `sonagi_heroine_cast_v2`
- **purpose**: v1 후보 불만족 → **기준 얼굴 중심 변주**
- **anchor**: `sonagi_heroine_cast_v1` · moody_pro · seed 88035 · c02  
  `…/sonagi_heroine_cast_v1__emoody_pro__s88035__c02.png`
- **look_id**: `cinematic_moody_v1`
- **method**: Moody I2I / i2i_lock from anchor (T2I 랜덤 재오디션 아님)

## Intent

v1 c02 얼굴 분위기(또렷한 눈·숏~미디엄 다크 웨이브·내추럴 피부)를 유지한 채  
시드·denoise·미세 프롬프트로 **같은 축 변주**를 본다.

## Review

1. `candidates/` + `contact_sheet.png` (anchor 포함 시 라벨 `_anchor`)
2. pick → promote
3. C expand `--engine i2i_lock`
