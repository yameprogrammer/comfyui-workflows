# RECIPE — 댄스 레퍼 → 내 캐릭 안무 (Wan Animate)

검증일: **2026-08-02** · 파일럿: Pretty Girl short → 남자 아이돌

---

## 재료

1. **캐릭 전신 스틸** (전신 보임, 손발 선명, 가능하면 중립 포즈)  
2. **댄스 RGB 영상** (권리 있는 레퍼, 전신이 보이면 구도 유리)  
3. ComfyUI 기동 (`:8188`) + 아래 모델/노드

---

## A. CLI (가장 쉬움)

```bash
cd F:\ComfyUI_workflows\agent_custom

python scripts/generate_wan22_animate.py \
  -i path\to\character.png \
  -v path\to\dance_ref.mp4 \
  -o path\to\out_dance.mp4 \
  --seed 42 \
  --hook-sec 3.8 \
  --face-strength 1.3 \
  --pose-strength 1.0
```

헤드룸(머리 잘림 완화)이 기본 켜져 있습니다.

---

## B. ComfyUI 사람 워크플로 (참고 그래프)

1. Load: `workflows/human/wan22/wan22_animate.json`  
2. 모델 로더에서:
   - Animate: `Wan2.2-Animate-14B-Q4_K.gguf` (또는 보유 quant)
   - VAE 2.1 / UMT5 / CLIP-ViT-H  
   - lightx2v + relight LoRA  
   - ViTPose-L + YOLO  
3. 입력:
   - **LoadImage** = 캐릭  
   - **VHS_LoadVideo** = 댄스 RGB (`force_rate=16`, `frame_load_cap≈49`)  
4. `WanVideoAnimateEmbeds`:
   - `face_strength` = **1.3**  
   - `pose_strength` = **1.0**  
   - width/height = **544 / 960**  
5. Sampler: steps **8**, scheduler **lcm**, cfg **1**  
6. Queue  

SAM2 서브그래프가 깨지면 **마스크 분기 끄고** pose+face+ref만 연결 (CLI와 동일).

---

## C. 머리 잘릴 때

1. CLI 기본 `--headroom` 유지  
2. 또는 레퍼를 전신이 더 보이게 다시 자름  
3. UI에서 DrawViTPose `retarget_padding` 48–64  
4. 캐릭 스틸을 캔버스 하단 정렬로 재배치  

---

## D. 기대치 체크리스트

- [ ] 캐릭 성별/의상이 레퍼로 바뀌지 않음  
- [ ] 팔·다리 타이밍이 레퍼와 대략 같음  
- [ ] 머리가 프레임 안에 있음  
- [ ] 손발 붕괴는 감수 범위  

실패 시: Fun Control로 돌아가지 말고 **face_strength↑ / hook 짧게 / 해상도·헤드룸** 먼저.
