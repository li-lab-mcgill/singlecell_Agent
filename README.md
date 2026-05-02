# singlecell_Agent

Python entry points use the package layout under `agents/`, `backend/`,
`pipelines/`, `prompts/`, and `rag/`.

## Setup

Create/activate an environment with Python 3.10-3.12 and install the Python
dependencies. Python 3.13 may work for the lightweight tests, but several
scientific packages can lag new Python releases.

```bash
python3 -m pip install -r requirements.txt
```

The full pipeline also expects valid model credentials for the selected
TextGrad/OpenAI engine and, for R-backed methods, an R environment from
`renv.lock`.

## Run the research pipeline

Run from the repository root. If you omit `--input_mod1`, the default is
`data/pbmc_RNA_count.annotated.h5ad` when present.

```bash
python3 default.py \
  --code-dir saved_code_pbmc10k \
  --results-dir results_pbmc10k \
  --notes-dir notes_pbmc10k \
  --input_mod1 data/pbmc_RNA_count.annotated.h5ad \
  --opt-step 10 \
  --max-fix-step 10 \
  --time-budget 3600
```

## Run the local frontend

```bash
python3 run_frontend.py \
  --input_mod1 data/pbmc_RNA_count.annotated.h5ad \
  --results-dir results_frontend
```

## Smoke checks

```bash
python3 -m unittest discover -s tests
python3 -m compileall -q .
```
