#!/bin/bash

# Modify this variable as needed to point to your submit scripts location:
scripts_path="/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/code/Preprocessing"

# Destination derivatives directory root
dest_dir_root="/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/derivatives"

# Default values
input_file=""
base_path=""
subject=""
session=""
run=""
run_denoise=false
run_gibbs=false
run_eddy=false
run_eddyqc=false
run_t1qc=false
test_mode=false

# Helper associative array to hold failure flags from CSV
declare -A failure_map

# Usage
usage() {
    echo "Usage: $0 [failure_report.csv | --subject sub-XXX --session ses-XXX [--run run-YYY]] --base-path /path/to/BIDS [--all | --denoise --gibbs --eddy --eddyqc --t1qc] [--test]"
    exit 1
}

# Check if first arg is a CSV file
if [[ $# -gt 0 && "$1" != --* ]]; then
    input_file="$1"
    shift
fi

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --base-path) shift; base_path="$1" ;;
        --subject) shift; subject="$1" ;;
        --session) shift; session="$1" ;;
        --run) shift; run="$1" ;;
        --all) run_denoise=true; run_gibbs=true; run_eddy=true; run_eddyqc=true; run_t1qc=true ;;
        --denoise) run_denoise=true ;;
        --gibbs)   run_gibbs=true ;;
        --eddy)    run_eddy=true ;;
        --eddyqc)  run_eddyqc=true ;;
        --t1qc)    run_t1qc=true ;;
        --test)    test_mode=true ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
    shift
done

# Validate inputs
if [[ -z "$base_path" ]]; then
    echo "Error: --base-path is required"
    usage
fi

if [[ -n "$input_file" && ( -n "$subject" || -n "$session" ) ]]; then
    echo "Error: Specify either a CSV input file or --subject/--session, not both."
    usage
fi

if [[ -z "$input_file" && ( -z "$subject" || -z "$session" ) ]]; then
    echo "Error: Either provide a CSV file or both --subject and --session."
    usage
fi

# Function to read CSV into failure_map
read_csv_failures() {
    local csv_file="$1"
    tail -n +2 "$csv_file" | while IFS=',' read -r sub ses run _ _ _ denoise_fail gibbs_fail eddy_fail _; do
        key="${sub}_${ses}_${run}"
        failure_map["$key,denoised"]="$denoise_fail"
        failure_map["$key,rmgibbs"]="$gibbs_fail"
        failure_map["$key,eddy"]="$eddy_fail"
    done
}

# Launch logic based on prior step success
process_subject_session() {
    local sub="$1"
    local ses="$2"
    local run="$3"
    local key="${sub}_${ses}_${run}"

    echo "Processing $sub $ses ${run:+$run}"

    if $run_denoise; then
        "$scripts_path"/submit_01_bids_denoise.sh "$base_path" "$sub" "$ses" "$run"
    fi

    if $run_gibbs; then
        if [[ "${failure_map[$key,denoised]}" != "True" ]]; then
            "$scripts_path"/submit_02_bids_gibbsringing.sh "$base_path" "$sub" "$ses" "$run"
        else
            echo "Skipping gibbs: denoised step failed for $key"
        fi
    fi

    if $run_eddy; then
        if [[ "${failure_map[$key,rmgibbs]}" != "True" ]]; then
            "$scripts_path"/submit_03_bids_eddy.sh "$base_path" "$sub" "$ses" "$run"
        else
            echo "Skipping eddy: rmgibbs step failed for $key"
        fi
    fi

    if $run_eddyqc; then
        if [[ "${failure_map[$key,eddy]}" != "True" ]]; then
            "$scripts_path"/submit_04_bids_eddyqc.sh "$base_path" "$sub" "$ses" "$run"
        else
            echo "Skipping eddyqc: eddy step failed for $key"
        fi
    fi

    if $run_t1qc; then
        local t1_qc_path="$dest_dir_root/$sub/$ses/t1_qc"
        if compgen -G "$t1_qc_path"/qc*.csv > /dev/null; then
            echo "T1 QC already exists at $t1_qc_path — skipping."
        else
            "$scripts_path"/submit_05_T1_qc.sh "$base_path" "$sub" "$ses"
        fi
    fi

    echo "Finished $sub $ses ${run:+$run}"
    echo "-----------------------------"
}

# If using a CSV, read it into memory first
if [[ -n "$input_file" ]]; then
    read_csv_failures "$input_file"
    tail -n +2 "$input_file" | while IFS=',' read -r sub ses run _; do
        [[ -z "$sub" || -z "$ses" ]] && continue
        process_subject_session "$sub" "$ses" "$run"

        if $test_mode; then
            echo "Test mode: stopping after first subject."
            break
        fi
    done
else
    process_subject_session "$subject" "$session" "$run"
fi

