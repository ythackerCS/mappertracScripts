#!/bin/bash

root_dir="/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/derivatives"

clean_empty_qc_dirs() {
    echo "Starting clean_empty_qc_dirs..."

    count_with=0
    count_without=0
    deleted_dirs=()

    while IFS= read -r -d '' dir; do
        if find "$dir" -type f -name "qc*.csv" -print -quit | grep -q .; then
            echo "QC found in: $dir"
            ((count_with++))
        else
            echo "No QC found — deleting: $dir"
            rm -rf "$dir"
            deleted_dirs+=("$dir")
            ((count_without++))
        fi
    done < <(find "$root_dir" -type d -name "t1_qc" -print0)

    echo -e "\nDeleted directories (no QC files):"
    for d in "${deleted_dirs[@]}"; do
        echo "$d"
    done

    echo -e "\nSummary:"
    echo "  With QC files   : $count_with"
    echo "  Deleted (empty) : $count_without"
    echo "  Total scanned   : $((count_with + count_without))"
}

clean_empty_bval_dirs() {
    echo "Starting clean_empty_bval_dirs in current directory..."

    deleted=0
    skipped=0

    is_recursive_empty() {
        local dir="$1"
        # Check if any file exists anywhere inside dir
        if find "$dir" -type f -print -quit | grep -q .; then
            return 1
        else
            return 0
        fi
    }

    while IFS= read -r -d '' dir; do
        if is_recursive_empty "$dir"; then
            echo "Deleting empty directory (recursively empty): $dir"
            rm -rf "$dir"
            ((deleted++))
        else
            echo "Skipping non-empty directory: $dir"
            ((skipped++))
        fi
    done < <(find . -type d -name '*\.bval*' -print0)

    echo -e "\nSummary:"
    echo "  Deleted empty .bval dirs : $deleted"
    echo "  Skipped non-empty dirs   : $skipped"
}

# Run both cleanup functions

clean_empty_qc_dirs
clean_empty_bval_dirs

