#!/bin/bash
#SBATCH --job-name=textgrad_try3
#SBATCH --output=logs/textgrad_try3_%j.out
#SBATCH --error=logs/textgrad_try3_%j.err
#SBATCH --time=04:00:00
#SBATCH --mem=16G
#SBATCH --cpus-per-task=4

set -euo pipefail

mkdir -p logs
mkdir -p try3
mkdir -p notes_try3

cd /home/mcb/users/ekourb/singlecell_Agent

source /home/mcb/users/ekourb/textgrad_agent/myenv/bin/activate

python default.py \
  --code-dir try3 \
  --results-dir try3 \
  --notes-dir notes_try3 \
  --input_mod1 /home/mcb/users/ekourb/singlecell_Agent/Datasets/RNA_count.h5ad \
  --opt-step 10 \
  --max-fix-step 10 \
  --time-budget 3600
