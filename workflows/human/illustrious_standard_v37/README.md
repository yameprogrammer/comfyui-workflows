# Illustrious Standard_V37

**출처:** [ComfyUI Image Workflows (Legendaer)](https://civitai.red/models/1386234/comfyui-image-workflows)  
**목적 (카드):** Workflow for **XL / Illustrious / NoobAI** Models  
**이 폴더:** 팩 4종 중 🟦 **Standard** 만 (Advanced의 축소판 = 일상 생성 메인)

| 파일 | 역할 |
|------|------|
| `Standard_V37.json` | 실 Comfy UI SSOT (미니그래프로 대체 금지) |
| `AGENT_GUIDE.md` | **출처 목적 + 사용법 + 기능 메뉴** (에이전트 필독) |
| `CAPABILITIES.json` | 기계 가독 purpose / pack roles / features |
| `GROUPS.json` | 그룹 → 노드 id (mode 0/4) |

```bash
python scripts/generate_illustrious_standard.py --list-features
python scripts/generate_illustrious_standard.py -p "masterpiece, best quality, 1girl, ..." -o out.png
```

팩 형제: Advanced(풀) · Basic(더 단순) · Detailer(기존 이미지 후처리) — 필요 시 **별도 도구**로 편입.
