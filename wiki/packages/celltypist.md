---
type: package
id: celltypist
version: ">=1.3"
citation: Dominguez Conde et al. 2022 Science
---

CellTypist provides pretrained logistic regression models for automated cell type annotation. Models are trained on curated atlases and cover immune, stromal, and epithelial cell types across multiple tissues and species.

Install: `pip install celltypist`

Key capabilities:
- `celltypist.annotate()` — annotates cells using a pretrained model
- `majority_voting=True` — smooths per-cell predictions using cluster membership, recommended for most use cases
- Model zoo: `Immune_All_Low.pkl` (fine-grained immune), `Immune_All_High.pkl` (coarse immune), `Pan_Fetal_Human.pkl` (fetal tissues)

Download models with `celltypist.models.download_models()`. Models are cached locally after first download. Best suited for immune cells — for non-immune tissues use marker-based or GPT-4 annotation.
