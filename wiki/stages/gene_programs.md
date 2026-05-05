---
type: stage
id: gene_programs
label: Gene Program Discovery
---

The gene program stage identifies coordinated sets of co-expressed genes (gene modules or programs) that represent underlying biological processes, pathways, or regulatory programs active across the dataset.

Gene programs go beyond pairwise correlation by finding latent factors — each factor represents a program with weights on genes and on cells. This is useful for understanding transcriptional heterogeneity within clusters, identifying stress responses, cell cycle effects, or tissue-specific programs.

Methods:
- **NMF (Non-negative Matrix Factorization)**: produces interpretable additive programs; each cell is a linear combination of programs
- **cNMF (consensus NMF)**: multiple NMF runs + consensus clustering for robust program discovery
- **MOFA+**: multi-modal; decomposes joint RNA+ATAC variation into shared and modality-specific factors
- **scVI latent space**: the scVI latent factors implicitly encode gene programs but are less interpretable than NMF

Edges:
- [[methods/nmf_programs]] modality: rna, multi
- [[methods/mofa_programs]] modality: multi
