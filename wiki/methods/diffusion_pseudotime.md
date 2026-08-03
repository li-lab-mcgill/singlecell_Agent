---
type: method
id: diffusion_pseudotime
label: Diffusion Pseudotime
---

Diffusion Pseudotime (DPT) orders cells along developmental trajectories by simulating a random walk on the cell-cell similarity graph. It computes pseudotime as the expected number of steps to reach a user-defined root cell.

DPT is implemented in scanpy via `sc.tl.diffmap()` (computes diffusion components) followed by `sc.tl.dpt()` (computes pseudotime given a root cell).

Key parameters:
- `root_cell`: index of the root cell; must be set manually based on known biology (e.g., the most immature progenitor based on marker expression)
- `n_dcs`: number of diffusion components; typically 10–15
- `n_branchings`: number of trajectory branches; 0 for linear trajectories

Output: `adata.obs["dpt_pseudotime"]` — pseudotime score per cell (0 = root, higher = more differentiated). Diffusion components stored in `adata.obsm["X_diffmap"]`.

DPT is appropriate for relatively simple, well-connected trajectories. For complex branching trees or RNA velocity-guided ordering, PAGA or scVelo are more appropriate.

Edges:
No executable backend tool currently implements diffusion pseudotime.
