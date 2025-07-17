#!/bin/bash

log_path=${1:-.}  # Default to current directory if no path is given

if [[ ! -d "$log_path" ]]; then
  echo "Invalid directory: $log_path"
  exit 1
fi

timestamp=$(date +'%Y%m%d_%H%M%S')
report_file="failure_report_${timestamp}.txt"
exec > >(tee "$report_file")  # Print to terminal and write to report file

echo "Recursively checking logs under: $log_path"
echo "Saving report to: $report_file"
echo "-------------------------------------------"

# Helper function for job check
check_job_logs() {
  local job_tag=$1
  local success_pattern=$2
  local fail_pattern=$3
  local extra_label=$4

  all_logs=$(find "$log_path" -type f -name "*${job_tag}*.out")
  fail_logs=$(grep -il "$fail_pattern" $all_logs 2>/dev/null)
  fail_count=$(echo "$fail_logs" | grep -c .)
  success_count=$(grep -il "$success_pattern" $all_logs 2>/dev/null | grep -c .)

  echo -e "\n${job_tag^^} | FAILURE: $fail_count  ${extra_label}COMPLETED: $success_count"

  if [[ $fail_count -gt 0 ]]; then
    echo "  Failed files:"
    echo "$fail_logs"
  fi
}

# --- Job-01 ---
check_job_logs "job-01" "COMPLETED" "FAIL"

# --- Job-02 ---
check_job_logs "job-02" "COMPLETED" "FAIL"

# --- Job-03 ---
all_logs=$(find "$log_path" -type f -name "*job-03*.out")
fail_logs=$(grep -il "fail" $all_logs 2>/dev/null)
fail_count=$(echo "$fail_logs" | grep -c .)
success_count=$(grep -il "Binary brain mask saved" $all_logs 2>/dev/null | grep -c .)
notfound_count=$(grep -il "filenotfounderror" $all_logs 2>/dev/null | grep -c .)

echo -e "\nJOB-03 | COMPLETE: $success_count  FAIL: $fail_count  FILENOTFOUNDERROR: $notfound_count"
if [[ $fail_count -gt 0 ]]; then
  echo "  Failed files:"
  echo "$fail_logs"
fi

echo -e "\nDone. Report saved to: $report_file"

