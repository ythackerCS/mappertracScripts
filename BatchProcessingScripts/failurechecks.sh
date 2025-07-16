#!/bin/bash

LOG_PATH="/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/misc/logs"
SUBJECTS_FILE="compatible_bval_subjects.txt"
BVAL_NEEDED=30   # minimum word count threshold

check_denoised() {
  echo "Checking runs with compatible bval scans (word count >= $BVAL_NEEDED) and their logs ..."

  total_failed=0
  declare -A failed_logs_map=()

  while IFS= read -r line; do
    if [[ "$line" == *"-MULTIPLE"* ]]; then
      base_path="${line%% -MULTIPLE*}"
      dwi_path="$base_path/dwi"

      if [[ ! -d "$dwi_path" ]]; then
        echo "Warning: directory $dwi_path not found, skipping."
        continue
      fi

      # Find all bval files in dwi_path
      bval_files=$(find "$dwi_path" -maxdepth 1 -type f -name '*_dwi.bval' 2>/dev/null)

      for bval_file in $bval_files; do
        word_count=$(wc -w < "$bval_file")
        if [ "$word_count" -ge "$BVAL_NEEDED" ]; then
          # Extract base run ID without extension and suffixes, e.g.:
          # sub-14735x1640_ses-SCAP1_run-01_dwi.bval -> sub-14735x1640_ses-SCAP1_run-01
          run_id=$(basename "$bval_file" | sed -E 's/_dwi\.bval$//')

          # Construct expected log filename pattern
          # Logs look like: sub-14735x1640_ses-SCAP1_job-01_denoise_run-01.out
          # We need to convert run_id like "sub-14735x1640_ses-SCAP1_run-01" to:
          # sub-14735x1640_ses-SCAP1_job-01_denoise_run-01.out
          # i.e. replace _run-XX with _job-01_denoise_run-XX

          log_prefix=$(echo "$run_id" | sed -E 's/_run-/_job-01_denoise_run-/')

          # Find matching logs
          matching_logs=$(find "$LOG_PATH" -type f -name "${log_prefix}.out" 2>/dev/null)

          for logf in $matching_logs; do
            if grep -iq 'FAILED' "$logf"; then
              echo "FAILED found in log: $logf (for run $run_id)"
              total_failed=$((total_failed + 1))
              failed_logs_map["$logf"]=1
            fi
          done
        else
          echo "Skipping $bval_file due to word count $word_count < $BVAL_NEEDED"
        fi
      done
    fi
  done < "$SUBJECTS_FILE"

  echo ""
  echo "Total failed logs found for compatible runs: $total_failed"
  if [ "$total_failed" -gt 0 ]; then
    echo "List of failed log files:"
    for f in "${!failed_logs_map[@]}"; do
      echo "$f"
    done | sort
  fi
}

if [[ "$1" == "--denoised" ]]; then
  check_denoised
else
  echo "Usage: $0 --denoised"
fi

