#!/bin/bash

bids_dir=/ceph/chpc/shared/shinjini_kundu_group/working/yash_test/tbm_autism-BIDS

sub=$1
ses=$2

mkdir -p ${bids_dir}/misc/jobs

mkdir -p ${bids_dir}/derivatives/${sub}/${ses}/work_dir

current_job=${bids_dir}/misc/jobs/s2_${sub}_${ses}.sh

if [[ -e ${current_job} ]]; then
          echo "MaPPeRTrac step 2 job for ${sub} ${ses} already exists. Remove it and rewrite."
          rm -f ${current_job}
fi

# THIS IS FOR THE PRIMAR JOB 
echo "MaPPeRTrac step 2 job for ${sub} ${ses} is being written..."

echo "#!/bin/bash" | tee -a ${current_job}

echo "#SBATCH --job-name=mapper-s2" | tee -a ${current_job}
# using tier 1 cpu partition for the primary job 
echo "#SBATCH --partition=tier1_cpu" | tee -a ${current_job}
# request one node 
echo "#SBATCH --nodes=1" | tee -a ${current_job}
# number of tasks 
echo "#SBATCH --ntasks-per-node=1" | tee -a ${current_job}
# number of cpus per task 
echo "#SBATCH --cpus-per-task=1" | tee -a ${current_job}
# using shinjini kundu account 
echo "#SBATCH --account=shinjini_kundu" | tee -a ${current_job}
#request 8 hours of processing time 
echo "#SBATCH --time=2:00:00" | tee -a ${current_job}
# 8 gbs of memeory 
echo "#SBATCH --mem=8gb" | tee -a ${current_job}


echo "#SBATCH -e ${bids_dir}/misc/output/${sub}_${ses}_s2_slurm-%j.err" | tee -a ${current_job}
echo "#SBATCH -o ${bids_dir}/misc/output/${sub}_${ses}_s2_slurm-%j.out" | tee -a ${current_job}

#activate enviornment 
echo "source /export/anaconda/anaconda3/anaconda3-2023.03/etc/profile.d/conda.sh" | tee -a ${current_job}
echo "conda activate /ceph/chpc/shared/shinjini_kundu_group/working/yash_test/mappertracenv" | tee -a ${current_job}

echo "cd ${bids_dir}/derivatives/${sub}/${ses}" | tee -a ${current_job}

#note we updated -n to number of cores we want for tasks: 8 (used to be 1) 
echo "mappertrac -s2 -o ${bids_dir}/derivatives --multi_container /ceph/chpc/shared/shinjini_kundu_group/working/yash_test/mappertraccontainers --slurm -n 1 -p tier1_gpu --walltime 1:00:00 --bank shinjini_kundu ${bids_dir}/derivatives/${sub}" | tee -a ${current_job}

echo "MaPPeRTrac step 2 job for ${sub} ${ses} is being submitted..."
sbatch ${current_job}

#HOW TO RUN
#./run_s1_free.sh sub-14706x320YTTRY ses-SCAP1
