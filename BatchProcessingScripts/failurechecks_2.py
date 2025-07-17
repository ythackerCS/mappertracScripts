#!/usr/bin/env python3
import os
import re
import csv
import sys

# Constants
SUBJECTS_FILE = "compatible_bval_subjects.txt"
LOG_PATH = "/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/misc/logs"
DERIVATIVES_PATH = "/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/derivatives"
OUTPUT_CSV = "failure_report.csv"
BVAL_NEEDED = 30

def word_count_in_file(filepath):
    if not os.path.isfile(filepath):
        return 0
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            return len(content.split())
    except Exception:
        return 0

def check_log_for_failure(logpath):
    """
    Returns True if any of 'failed', 'failure', or 'error' (case-insensitive) is found in log.
    """
    error_keywords = ['fail', 'failure', 'FileNotFoundError']
    if not os.path.isfile(logpath):
        return False
    try:
        with open(logpath, 'r', errors='ignore') as f:
            for line in f:
                lower_line = line.lower()
                if any(keyword in lower_line for keyword in error_keywords):
                    return True
    except Exception:
        return False
    return False

def parse_sub_ses_run_from_path(bval_path):
    filename = os.path.basename(bval_path)
    m = re.match(r'(sub-[^_]+)_ses-([^_]+)(?:_run-(\d+))?_dwi\.bval', filename)
    if m:
        sub = m.group(1)
        ses = m.group(2)
        run = m.group(3) if m.group(3) else '--'
        return sub, ses, run
    else:
        return None, None, None

def main():
    check_denoised_flag = '--denoised' in sys.argv or '--all' in sys.argv
    check_rmgibbs_flag = '--rmgibbs' in sys.argv or '--all' in sys.argv
    check_eddy_flag = '--eddy' in sys.argv or '--all' in sys.argv
    check_eddyqc_flag = '--eddyqc' in sys.argv or '--all' in sys.argv

    rows = []

    with open(SUBJECTS_FILE, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    for line in lines:
        if ' -' not in line:
            print(f"Warning: line missing expected ' -' delimiter: {line}")
            continue
        base_path, suffix = line.split(' -', 1)

        if suffix == 'MULTIPLE':
            dwi_dir = os.path.join(base_path, 'dwi')
            if not os.path.isdir(dwi_dir):
                print(f"Warning: dwi folder not found at {dwi_dir}, skipping.")
                continue
            bval_files = [f for f in os.listdir(dwi_dir) if f.endswith('_dwi.bval')]
        else:
            bval_files = [suffix]
            dwi_dir = os.path.join(base_path, 'dwi')

        for bval_file in bval_files:
            bval_path = os.path.join(dwi_dir, bval_file)
            if not os.path.isfile(bval_path):
                print(f"Warning: Specified bval file {bval_path} does not exist, skipping.")
                continue

            sub, ses, run = parse_sub_ses_run_from_path(bval_path)
            if not sub:
                print(f"Warning: Could not parse subject/session/run from {bval_file}, skipping.")
                continue

            bval_wc = word_count_in_file(bval_path)
            if bval_wc < BVAL_NEEDED:
                continue

            dwi_file = bval_file.replace('.bval', '.nii.gz').replace('_bval', '_dwi')
            dwi_path = os.path.join(dwi_dir, dwi_file)

            row = {
                'subject': sub,
                'session': ses,
                'run': run,
                'bval_word_count': bval_wc,
                'dwi_file': dwi_file,
                'dwi_path': dwi_path
            }

            base_name = f"{sub}_ses-{ses}" + (f"_run-{run}" if run != '--' else "")
            deriv_dir = os.path.join(DERIVATIVES_PATH, sub, f"ses-{ses}", "preproc")

            ### DENOISED CHECK ###
            if check_denoised_flag:
                denoised_file = base_name + "_dwi_denoised.nii.gz"
                denoised_path = os.path.join(deriv_dir, denoised_file)

                log_file = base_name + "_job-01_denoise.out"
                log_path = os.path.join(LOG_PATH, log_file)

                log_has_errors = check_log_for_failure(log_path)
                output_exists = os.path.isfile(denoised_path)

                row['denoised_log_has_errors'] = log_has_errors
                row['denoised_failed'] = log_has_errors or not output_exists

            ### RMGIBBS CHECK ###
            if check_rmgibbs_flag:
                rmgibbs_file = base_name + "_dwi_denoised_rmgibbs.nii.gz"
                rmgibbs_path = os.path.join(deriv_dir, rmgibbs_file)

                log_file = base_name + "_job-02_rmgibbs.out"
                log_path = os.path.join(LOG_PATH, log_file)

                log_has_errors = check_log_for_failure(log_path)
                output_exists = os.path.isfile(rmgibbs_path)

                row['rmgibbs_log_has_errors'] = log_has_errors
                row['rmgibbs_failed'] = log_has_errors or not output_exists

            ### EDDY CHECK ###
            if check_eddy_flag:
                if not row.get('rmgibbs_failed', False):
                    log_file = base_name + "_job-03_eddy.out"
                    log_path = os.path.join(LOG_PATH, log_file)

                    log_has_errors = check_log_for_failure(log_path)

                    brain_file = base_name + "_dwi_denoised_rmgibbs_eddy_brain.nii.gz"
                    mask_file = base_name + "_dwi_denoised_rmgibbs_eddy_mask.nii.gz"

                    brain_path = os.path.join(deriv_dir, brain_file)
                    mask_path = os.path.join(deriv_dir, mask_file)

                    output_exists = os.path.isfile(brain_path) and os.path.isfile(mask_path)

                    row['eddy_log_has_errors'] = log_has_errors
                    row['eddy_failed'] = log_has_errors or not output_exists
                else:
                    row['eddy_failed'] = False
                    row['eddy_log_has_errors'] = False

            ### EDDYQC CHECK ###
            if check_eddyqc_flag:
                # Placeholder: You can implement specific file or log checks here
                row['eddyqc_failed'] = False  # Currently defaulting to no failure

            rows.append(row)

    # Determine which failure/log columns to include in the CSV
    failure_cols = [
        col for col in [
            'eddyqc_failed', 'eddy_failed', 'eddy_log_has_errors',
            'rmgibbs_failed', 'rmgibbs_log_has_errors',
            'denoised_failed', 'denoised_log_has_errors'
        ] if any(col in r for r in rows)
    ]

    # Sort rows: by failure flags first, then by descending bval word count
    def sort_key(r):
        flags = tuple(r.get(col, False) for col in failure_cols)
        return flags + (-r.get('bval_word_count', 0),)

    rows.sort(key=sort_key, reverse=True)

    # Final CSV fieldnames
    fieldnames = ['subject', 'session', 'run', 'dwi_file', 'dwi_path', 'bval_word_count'] + failure_cols

    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # Summary report
    print(f"\nReport written to: {OUTPUT_CSV}")
    print(f"Total scans processed (bval_wc >= {BVAL_NEEDED}): {len(rows)}")
    for col in failure_cols:
        count = sum(1 for r in rows if r.get(col, False))
        print(f"Scans with {col}: {count}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: failurechecks.py [--denoised] [--rmgibbs] [--eddy] [--eddyqc] [--all]")
        sys.exit(1)
    main()


