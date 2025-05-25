#!/bin/bash

output_file="compatible_bval_subjects.txt"
bvalneeded=30
data_root="/ceph/chpc/shared/shinjini_kundu_group/working/yash_test/tbm_autism-BIDS/sourcedata2"

declare -A session_counts=()
declare -A session_bvalfiles=()

> "$output_file"

# Count total session folders excluding 'tmp_dcm2bids'
total_sessions=$(find "$data_root" -type d -name "ses-*" ! -path "*/tmp_dcm2bids/*" | wc -l)

# Scan for qualifying bval files
while read -r bval_file; do
  word_count=$(wc -w < "$bval_file")
  if [ "$word_count" -ge "$bvalneeded" ]; then
    ses_dir=$(dirname "$bval_file" | sed -E 's|(.*?/ses-[^/]+).*|\1|')

    # Check anat directory for t1w scan
    anat_dir="$ses_dir/anat"
    if [ -d "$anat_dir" ] && ls "$anat_dir"/*t1w*.nii.gz >/dev/null 2>&1; then
      ((session_counts["$ses_dir"]++))
      session_bvalfiles["$ses_dir"]+="${bval_file##*/} "
    fi
  fi
done < <(find "$data_root" -type f -name "*_dwi.bval")

count=0
for ses_dir in "${!session_counts[@]}"; do
  if [ "${session_counts[$ses_dir]}" -gt 1 ]; then
    echo "${ses_dir} -MULTIPLE" >> "$output_file"
  else
    bval_tag=$(echo "${session_bvalfiles[$ses_dir]}" | awk '{print $1}')
    echo "${ses_dir} -${bval_tag}" >> "$output_file"
  fi
  ((count++))
done

echo "Using bvalneeded threshold: $bvalneeded" >> "$output_file"
echo "Total matching sessions: $count" >> "$output_file"
echo "Total session folders (excluding tmp_dcm2bids): $total_sessions" >> "$output_file"

echo "Using bvalneeded threshold: $bvalneeded"
echo "Total matching sessions: $count"
echo "Total session folders (excluding tmp_dcm2bids): $total_sessions"

