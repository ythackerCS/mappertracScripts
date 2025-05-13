#!/bin/bash

sub=$1
ses=$2

bids_dir=/ceph/chpc/shared/shinjini_kundu_group/working/yash_test/tbm_autism-BIDS

mkdir -p ${bids_dir}/misc/jobs

current_job=${bids_dir}/misc/jobs/s1_${sub}_${ses}.sh

if [[ -e ${current_job} ]]; then
          echo "MaPPeRTrac step 1 job for ${sub} ${ses} already exists. Remove it and rewrite."
          rm -f ${current_job}
fi

# THIS IS FOR THE PRIMAR JOB 
echo "MaPPeRTrac step 1 job for ${sub} ${ses} is being written..."

echo "#!/bin/bash" | tee -a ${current_job}
echo "#SBATCH --job-name=mapper-s1" | tee -a ${current_job}
# using free tier cpu partiition 
echo "#SBATCH --partition=free" | tee -a ${current_job}
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


echo "#SBATCH -e ${bids_dir}/misc/output/${sub}_${ses}_s1_slurm-%j.err" | tee -a ${current_job}
echo "#SBATCH -o ${bids_dir}/misc/output/${sub}_${ses}_s1_slurm-%j.out" | tee -a ${current_job}


echo "cd ${bids_dir}/derivatives/${sub}/${ses}" | tee -a ${current_job}
echo "mappertrac -s1 -o ${bids_dir}/derivatives --multi_container /ceph/chpc/shared/shinjini_kundu_group/working/yash_test/mappertraccontainers --slurm -n 1 -p free --walltime 2:00:00 --bank shinjini_kundu --edgelist tiny ${bids_dir}/derivatives/${sub}" | tee -a ${current_job}

echo "MaPPeRTrac step 1 job for ${sub} ${ses} is being submitted..."
sbatch ${current_job}

#HOW TO RUN
#./run_s1_free.sh sub-14706x320YTTRY ses-SCAP1
