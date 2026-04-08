#!/bin/bash
#SBATCH --job-name=sc_agent
#SBATCH --partition=li-gpus
#SBATCH --account=yueli-2026
#SBATCH --qos=li-qos
#SBATCH --time=20:00:00
#SBATCH --mem=32G
#SBATCH --gpus=1
#SBATCH --output=logs/sc_agent_%j.out
#SBATCH --error=logs/sc_agent_%j.err

mkdir -p logs

LOCAL_ENV=/tmp/myenv_$SLURM_JOB_ID
echo "Copying env to $LOCAL_ENV ..."
cp -r /home/mcb/users/ekourb/textgrad_agent/myenv $LOCAL_ENV
echo "Done copying env."

source $LOCAL_ENV/bin/activate

cd /home/mcb/users/ekourb/singlecell_Agent

python -u default.py \
  --input_mod1 /home/mcb/users/ekourb/singlecell_Agent/Datasets/RNA_count.h5ad \
  --dataset-dir /home/mcb/users/ekourb/singlecell_Agent/Datasets \
  --api-dir /home/mcb/users/ekourb/singlecell_Agent/runsv4 \
  --engine gpt-5 \
  --opt-step 10 \
  --max-fix-step 30 \
  --time-budget 3600 \
  --stagnation_steps_limit 5 \
  --delta-min 0.005

# Cleanup local env copy
rm -rf $LOCAL_ENV