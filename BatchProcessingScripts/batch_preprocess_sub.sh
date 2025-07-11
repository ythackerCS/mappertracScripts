#!/bin/bash

#Example run: ./run_all_submissions.sh compatible_bval_subjects.txt --base-path /ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS --all --test


# Usage message
usage() {
    echo "Usage: $0 path_to_input_list.txt --base-path /path/to/BIDS [--all | --denoise --gibbs --eddy --eddyqc --t1qc] [--test]"
    echo
    echo "Example:"
    echo "  $0 compatible_bval_subjects.txt --base-path /my/path --all"
    echo "  $0 compatible_bval_subjects.txt --base-path /my/path --denoise --test"
    exit 1
}

# Check minimum argument count
if [ $# -lt 3 ]; then
    usage
fi

# Input file
input_file="$1"
shift

# Default values
base_path=""
run_denoise=false
run_gibbs=false
run_eddy=false
run_eddyqc=false
run_t1qc=false
test_mode=false

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --base-path)
            shift
            base_path="$1"
            ;;
        --all)
            run_denoise=true
            run_gibbs=true
            run_eddy=true
            run_eddyqc=true
            run_t1qc=true
            ;;
        --denoise) run_denoise=true ;;
        --gibbs)   run_gibbs=true ;;
        --eddy)    run_eddy=true ;;
        --eddyqc)  run_eddyqc=true ;;
        --t1qc)    run_t1qc=true ;;
        --test)    test_mode=true ;;
        *) echo "Unknown option: $1" ; usage ;;
    esac
    shift
done

# Validate base_path
if [[ -z "$base_path" ]]; then
    echo "Error: --base-path is required"
    usage
fi

# Process each line of the input file
while IFS= read -r line; do
    sub=$(echo "$line" | grep -o 'sub-[^/]*')
    ses=$(echo "$line" | grep -o 'ses-[^ ]*')

    if [[ -z "$sub" || -z "$ses" ]]; then
        echo "Skipping invalid line: $line"
        continue
    fi

    echo "Processing $sub $ses"

    if $run_denoise; then
        echo "Running denoise..."
        ./submit_01_bids_denoise.sh "$base_path" "$sub" "$ses"
    fi

    if $run_gibbs; then
        echo "Running gibbs ringing removal..."
        ./submit_02_bids_gibbsringing.sh "$base_path" "$sub" "$ses"
    fi

    if $run_eddy; then
        echo "Running eddy..."
        ./submit_03_bids_eddy.sh "$base_path" "$sub" "$ses"
    fi

    if $run_eddyqc; then
        echo "Running eddy QC..."
        ./submit_04_bids_eddyqc.sh "$base_path" "$sub" "$ses"
    fi

    if $run_t1qc; then
        echo "Running T1 QC..."
        ./submit_05_T1_qc.sh "$base_path" "$sub" "$ses"
    fi

    echo "Finished $sub $ses"
    echo "-----------------------------"

    if $test_mode; then
        echo "Test mode enabled: exiting after first subject."
        break
    fi

done < "$input_file"
