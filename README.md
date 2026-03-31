# singlecell_Agent

Run from the repository root:

```bash
python default.py \
  --code-dir saved_code_pbmc10k \
  --results-dir results_pbmc10k \
  --notes-dir notes_pbmc10k \
  --input_mod1 pbmc10k_annotated.h5ad \
  --opt-step 10 \
  --max-fix-step 10 \
  --time-budget 3600
```
```bash
python default.py \
  --input_mod1 /home/mcb/users/ekourb/singlecell_Agent/Datasets/RNA_count.h5ad \
  --dataset-dir /home/mcb/users/ekourb/singlecell_Agent/Datasets \
  --engine gpt-5 \
  --opt-step 10 \
  --max-fix-step 10 \
  --time-budget 3600 \
  --stagnation_steps_limit 5 \
  --delta-min 0.005
```

