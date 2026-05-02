#!/bin/bash
#SBATCH -A yueli-2026
#SBATCH -p li-gpus
#SBATCH --qos=li-qos
#SBATCH --job-name=ad_xtrimo_train
#SBATCH --output=/home/mcb/users/wdong12/singlecell_Agent/jobs/%x_%j.out
#SBATCH --time=12:00:00
#SBATCH --mem=64G
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1

cd /home/mcb/users/wdong12/singlecell_Agent
mkdir -p jobs logs

source ~/.bashrc
conda activate scetm

python3 default.py \
  --code-dir saved_code_pbmc10k \
  --results-dir results_pbmc10k \
  --notes-dir notes_pbmc10k \
  --input_mod1 data/pbmc_RNA_count.annotated.h5ad \
  --opt-step 10 \
  --max-fix-step 10 \
  --time-budget 3600
