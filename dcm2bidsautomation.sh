#!/bin/bash

# Load required module
module load dcm2niix/4.11.23

input_base="/ceph/chpc/shared/shinjini_kundu_group/working/yash/unzippedsubjects"
output_base="/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/sourcedata2"
config_file="/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/mappertracScripts/dcm2bids_largesample.json"

count=0
#max_count=20

for folder in "$input_base"/*; do
  if [ -d "$folder" ]; then
    folder_name=$(basename "$folder")

    session_part="${folder_name##*_}"
    subject_part="${folder_name%_*}"
    subject_clean=$(echo "$subject_part" | tr -d '._')

    subj_id="sub-${subject_clean}"
    ses_id="ses-${session_part}"

    echo "Processing folder: $folder_name"
    echo "Subject ID: $subj_id"
    echo "Session ID: $ses_id"

    dcm2bids -d "$folder" -p "$subj_id" -s "$ses_id" -o "$output_base" --do_not_reorder_entities --force_dcm2bids -c "$config_file"

    ((count++))
    #if [ "$count" -ge "$max_count" ]; then
    #  echo "Processed $max_count folders, stopping."
    #  break
    #fi
  fi
done

