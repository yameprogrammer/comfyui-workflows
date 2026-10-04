# Krea2 LoRA — 에이전트 SSOT

- **조회**: `python scripts/krea2_lora_status.py`
- **코드**: `lib/krea2_lora_catalog.py`
- **넣는 곳**: `F:\model\loras\Krea2\`

가중치만 넣으면 목록에 보인다. 옆에 `<파일이름>.purpose.json`의 `purpose`와 `when`이 채워져야 에이전트가 생성에 붙인다. 비어 있으면 `unclassified`이고 `--lora`에 넣지 않는다.

용도 문장은 사용자가 쓰지 않는다. 받은 페이지(Civitai, Hugging Face)를 알려 주면 그 모델 카드의 설명·강도·트리거로 채운다.

## 고르는 규칙

1. Krea 스틸 전에 `krea2_lora_status.py` 또는 `recommend "<룩>"`을 본다.
2. `when`이 샷과 맞는 ready 항목이 있을 때만 그 CLI를 쓴다. 최대 하나.
3. `slot=t2i`만 `generate_krea --lora`. `slot=nsfw_t2i`는 `generate_krea_nsfw --lora`이고 성인 18+만.
4. `identity_edit`는 `generate_krea2_identity_edit`. `control`은 `generate_krea2_control`.
5. 깨끗한 실사 키프레임은 LoRA 없이 `generate_krea`.

## 용도 카드

`python scripts/krea2_lora_status.py draft SomeLora.safetensors`가 빈 카드를 만든다. 덮어쓰지 않는다.

```json
{
  "id": "some_lora",
  "slot": "t2i",
  "purpose": "한 줄 용도",
  "when": ["이 룩이 샷의 목적일 때"],
  "when_not": ["깨끗한 실사 기본 키프레임"],
  "strength": 0.7,
  "trigger": null,
  "keywords": ["brush", "붓"]
}
```

`slot`은 `t2i` | `nsfw_t2i` | `identity_edit` | `control`.

같은 파일이 `Krea 2` 폴더에 하드링크로 또 있으면 한 번만 나온다.
