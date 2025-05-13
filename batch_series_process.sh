#!/bin/bash

output_file="unique_series_descriptions.txt"
helper_path="/ceph/chpc/shared/shinjini_kundu_group/working/yash_test/tbm_autism-BIDS/code/tmp_dcm2bids/helper/tbm-autism"
tmp_dir="/ceph/chpc/shared/shinjini_kundu_group/working/yash_test/tbm_autism-BIDS/code/tmp_dcm2bids"  # Path to tmp_dcm2bids
touch $output_file  # Ensure the file exists

# Only process the first folder for testing
for folder in 15024.x1_60_FCAP1 14723.x10_60_FCAP1  14751.x6_60_FCAP1   14784.x15_50_FCAP1  14819.x1_60_FCAP1   14851.x1_60_FCAP1   14879.x4_60_FCAP1   14909.x13_60_FCAP1  14933.x1_60_FCAP1  14969.x7_20_SCAP1   15031.x1_60_FCAP1 14723.x17_60_FCAP1  14755.x15_60_FCAP1  14786.x23_60_FCAP1  14820.x12_50_FCAP1; do

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

