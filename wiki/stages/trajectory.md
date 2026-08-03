---
type: stage
id: trajectory
label: Trajectory Analysis
---

The trajectory stage orders cells along a continuous developmental or differentiation path, recovering pseudotime — an inferred ordering that reflects biological progression rather than collection time.

Trajectory analysis is appropriate when the biology is continuous (e.g., stem cell differentiation, immune activation) rather than discrete. For discrete cell types, clustering and annotation is sufficient.

Key concepts:
- **Pseudotime**: a scalar value per cell representing position along the trajectory
- **Root cell**: the starting point, usually set by the user based on known biology (e.g., progenitor marker expression)
- **Branching**: some trajectories bifurcate; methods handle this differently

Edges:
- [[methods/diffusion_pseudotime]] modality: rna, multi
