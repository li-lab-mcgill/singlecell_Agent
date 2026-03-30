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


python default.py \
  --code-dir try1 \
  --results-dir try1 \
  --notes-dir notes_try1\
  --input_mod1 /home/mcb/users/ekourb/singlecell_Agent/Datasets/RNA_count.h5ad \
  --opt-step 10 \
  --max-fix-step 10 \
  --time-budget 3600

python default.py \
  --code-dir try2 \
  --results-dir try2 \
  --notes-dir notes_try2\
  --input_mod1 /home/mcb/users/ekourb/singlecell_Agent/Datasets/RNA_count.h5ad \
  --opt-step 10 \
  --max-fix-step 10 \
  --time-budget 3600

python default.py \
  --code-dir try4 \
  --results-dir try4 \
  --notes-dir notes_try4 \
  --dataset-dir /home/mcb/users/ekourb/singlecell_Agent/Datasets \
  --input_mod1 /home/mcb/users/ekourb/singlecell_Agent/Datasets/RNA_count.h5ad \
  --opt-step 10 \
  --max-fix-step 10 \
  --time-budget 3600
