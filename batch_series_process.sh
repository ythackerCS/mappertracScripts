#!/bin/bash

# Load necessary module
module load dcm2niix/4.11.23

# Activate conda environment
source ~/miniconda/etc/profile.d/conda.sh
conda activate /ceph/chpc/shared/shinjini_kundu_group/working/yash_test/mappertracenv

output_file="unique_series_descriptions2.txt"
helper_path="/ceph/chpc/shared/shinjini_kundu_group/working/yash_test/tbm_autism-BIDS/mappertracScripts/tmp_dcm2bids/helper/tbm-autism"
tmp_dir="/ceph/chpc/shared/shinjini_kundu_group/working/yash_test/tbm_autism-BIDS/mappertracScripts/tmp_dcm2bids"

touch $output_file  # Ensure the file exists

# Only process the first folder for testing
for folder in 14708.x10_60_FCAP1 14741.x23_60_FCAP1 14770.x7_20_SCAP1 14814.x1_60_FCAP1 14845.x1_60_FCAP1 14870.x11_60_FCAP1 14902.x1_60_FCAP1 14926.x1_60_FCAP1 14962.x1_60_FCAP1 14999.x1_60_FCAP1 \
              14711.x7_20_SCAP1 14742.x7_50_FCAP1 14770.x8_60_FCAP1 14816.x10_60_FCAP1 14846.x1_60_FCAP1 14871.x1_60_FCAP1 14906.x1_50_FCAP1 14927.x2_50_FCAP1 14967.x23_60_FCAP1 15008.x1_60_FCAP1 \
              14711.x8_20_SCAP1 14744.x5_50_FCAP1 14780.x3_60_FCAP1 14816.x12_60_FCAP1 14847.x1_60_FCAP1 14873.x1_50_FCAP1 14908.x35_60_FCAP1 14928.x1_60_FCAP1 14967.x25_60_FCAP1 15015.x1_50_FCAP1 \
              14714.x18_60_FCAP1 14747.x10_60_FCAP1 14781.x16_60_FCAP1 14817.x1_60_FCAP1 14849.x1_60_FCAP1 14878.x1_60_FCAP1 14908.x36_60_FCAP1 14931.x1_60_FCAP1 14969.x4_20_SCAP1 15024.x1_60_FCAP1 \
              14723.x10_60_FCAP1 14751.x6_60_FCAP1 14784.x15_50_FCAP1 14819.x1_60_FCAP1 14851.x1_60_FCAP1 14879.x4_60_FCAP1 14909.x13_60_FCAP1 14933.x1_60_FCAP1 14969.x7_20_SCAP1 15031.x1_60_FCAP1 \
              14723.x17_60_FCAP1 14755.x15_60_FCAP1 14786.x23_60_FCAP1 14820.x12_50_FCAP1; do

  echo "Running dcm2bids_helper for $folder"
  dcm2bids_helper -n tbm-autism -d /ceph/chpc/shared/shinjini_kundu_group/working/yash_test/compatiblesubjects/$folder

  echo "Running getseries.py"
  python getseries.py "$helper_path" > temp_series_output.txt

  # Extract series descriptions, remove "- ", deduplicate
  grep '^-' temp_series_output.txt | sed 's/^- //' | sort -u > new_series.txt

  # Add only new unique entries to the output file
  comm -23 new_series.txt <(sort "$output_file") >> "$output_file"

  # Clear the contents of tmp_dcm2bids
  echo "Clearing contents of tmp_dcm2bids directory..."
  rm -rf $tmp_dir/*

  # Break after the first folder for testing
  #break
done

# Cleanup
rm -f temp_series_output.txt new_series.txt
