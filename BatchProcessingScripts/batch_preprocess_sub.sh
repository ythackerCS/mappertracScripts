#!/bin/bash

# Modify this variable as needed to point to your submit scripts location:
scripts_path="/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/code/Preprocessing"

# Example run:
# ./run_all_submissions.sh compatible_bval_subjects.txt --base-path /ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS --all --test

# Usage message
usage() {
    echo "Usage: $0 [path_to_input_list.txt | --subject sub-XXX --session ses-XXX] --base-path /path/to/BIDS [--all | --denoise --gibbs --eddy --eddyqc --t1qc] [--test]"
    echo
    echo "Examples:"
    echo "  $0 compatible_bval_subjects.txt --base-path /my/path --all"
    echo "  $0 --subject sub-01 --session ses-01 --base-path /my/path --denoise --test"
    exit 1
}

# Default values
input_file=""
base_path=""
subject=""
session=""
run_denoise=false
run_gibbs=false
run_eddy=false
run_eddyqc=false
run_t1qc=false
test_mode=false

# Validate scripts_path directory exists
if [[ ! -d "$scripts_path" ]]; then
    echo "Error: scripts path directory does not exist: $scripts_path"
    exit 1
fi

# Parse positional argument or options
# If first arg doesn't start with "--", treat it as input_file
if [[ $# -gt 0 && "$1" != --* ]]; then
    input_file="$1"
    shift
fi

# Parse options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --base-path)
            shift
            base_path="$1"
            ;;
        --subject)
            shift
            subject="$1"
            ;;
        --session)
            shift
            session="$1"
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

# Validate inputs
if [[ -z "$base_path" ]]; then
    echo "Error: --base-path is required"
    usage
fi

if [[ -n "$input_file" && ( -n "$subject" || -n "$session" ) ]]; then
    echo "Error: Specify either an input file or --subject/--session, not both."
    usage
fi

if [[ -z "$input_file" && ( -z "$subject" || -z "$session" ) ]]; then
    echo "Error: Either provide input file or both --subject and --session."
    usage
fi

# Normalize scripts_path (remove trailing slash if any)
scripts_path="${scripts_path%/}"

process_subject_session() {
    local sub=$1
    local ses=$2

    echo "Processing $sub $ses"

    if $run_denoise; then
        echo "Running denoise..."
        "$scripts_path"/submit_01_bids_denoise.sh "$base_path" "$sub" "$ses"
    fi

    if $run_gibbs; then
        echo "Running gibbs ringing removal..."
        "$scripts_path"/submit_02_bids_gibbsringing.sh "$base_path" "$sub" "$ses"
    fi

    if $run_eddy; then
        echo "Running eddy..."
        "$scripts_path"/submit_03_bids_eddy.sh "$base_path" "$sub" "$ses"
    fi

    if $run_eddyqc; then
        echo "Running eddy QC..."
        "$scripts_path"/submit_04_bids_eddyqc.sh "$base_path" "$sub" "$ses"
    fi

    if $run_t1qc; then
        echo "Running T1 QC..."
        "$scripts_path"/submit_05_T1_qc.sh "$base_path" "$sub" "$ses"
    fi

    echo "Finished $sub $ses"
    echo "-----------------------------"
}

# Main logic

if [[ -n "$input_file" ]]; then
    # Process list from file
    while IFS= read -r line; do
        sub=$(echo "$line" | grep -o 'sub-[^/ ]*')
        ses=$(echo "$line" | grep -o 'ses-[^/ ]*')

        if [[ -z "$sub" || -z "$ses" ]]; then
            echo "Skipping invalid line: $line"
            continue
        fi

        process_subject_session "$sub" "$ses"

        if $test_mode; then
            echo "Test mode enabled: exiting after first subject."
            break
        fi
    done < "$input_file"

else
    # Single subject/session provided
    process_subject_session "$subject" "$session"
fi
