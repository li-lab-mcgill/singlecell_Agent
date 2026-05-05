---
type: stage
id: normalize
label: Normalization
---

The normalization stage scales raw counts to remove technical variation in sequencing depth, then applies a variance-stabilizing transformation to prepare expression values for downstream linear methods (PCA, Harmony).

RNA normalization precedes feature selection and embedding. ATAC data uses TF-IDF normalization instead (handled inside the embed stage via spectral embedding).

Edges:
- [[methods/library_size_normalization]] modality: rna, multi
- [[methods/variance_stabilization]] modality: rna, multi
