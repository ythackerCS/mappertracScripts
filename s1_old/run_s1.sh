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

echo "MaPPeRTrac step 1 job for ${sub} ${ses} is being written..."

echo "#!/bin/bash" | tee -a ${current_job}
echo "#SBATCH --job-name=mapper-s1" | tee -a ${current_job}
echo "#SBATCH --partition=cpu.queue" | tee -a ${current_job}
echo "#SBATCH --nodes=1" | tee -a ${current_job}
echo "#SBATCH --ntasks-per-node=1" | tee -a ${current_job}
echo "#SBATCH --cpus-per-task=1" | tee -a ${current_job}
echo "#SBATCH --account=your.cluster.account" | tee -a ${current_job}
echo "#SBATCH -e ${bids_dir}/misc/output/${sub}_${ses}_s1_slurm-%j.err" | tee -a ${current_job}
echo "#SBATCH -o ${bids_dir}/misc/output/${sub}_${ses}_s1_slurm-%j.out" | tee -a ${current_job}
echo "#SBATCH --time=12:00:00" | tee -a ${current_job}
echo "#SBATCH --mem=10gb" | tee -a ${current_job}

echo "cd ${bids_dir}/derivatives/${sub}/${ses}" | tee -a ${current_job}
echo "mappertrac -s1 -o ${bids_dir}/derivatives --multi_container /ceph/chpc/shared/shinjini_kundu_group/working/yash_test/mappertraccontainers --slurm -n 1 -p cpu --walltime 12:00:00 --bank your.cpu.account --edgelist tiny ${bids_dir}/derivatives/${sub} | tee -a ${current_job}

echo "MaPPeRTrac step 1 job for ${sub} ${ses} is being submitted..."
sbatch ${current_job}

