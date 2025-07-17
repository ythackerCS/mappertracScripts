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
    if not os.path.isfile(logpath):
        return False
    try:
        with open(logpath, 'r', errors='ignore') as f:
            for line in f:
                if 'FAILED' in line.upper():
                    return True
    except Exception:
        return False
    return False

def parse_sub_ses_run_from_path(bval_path):
    # Expected format in filename: sub-XXXxYYY_ses-XXX[_run-ZZ]_dwi.bval
    filename = os.path.basename(bval_path)
    # Regex to parse sub, ses, optional run
    m = re.match(r'(sub-[^_]+)_ses-([^_]+)(?:_run-(\d+))?_dwi\.bval', filename)
    if m:
        sub = m.group(1)
        ses = m.group(2)
        run = m.group(3) if m.group(3) else '--'
        return sub, ses, run
    else:
        return None, None, None

def main():

    # Flags for checking
    check_denoised_flag = '--denoised' in sys.argv or '--all' in sys.argv
    check_rmgibbs_flag = '--rmgibbs' in sys.argv or '--all' in sys.argv
    check_eddy_flag = '--eddy' in sys.argv or '--all' in sys.argv
    check_eddyqc_flag = '--eddyqc' in sys.argv or '--all' in sys.argv

    rows = []

    with open(SUBJECTS_FILE, 'r') as f:
        lines = [line.strip() for line in f if line.strip()]

    for line in lines:
        # Expect lines like:
        # /path/to/sub-14753x520/ses-SCAP1 -MULTIPLE
        # or
        # /path/to/sub-14921x820/ses-SCAP1 -sub-14921x820_ses-SCAP1_run-01_dwi.bval
        if ' -' not in line:
            print(f"Warning: line missing expected ' -' delimiter: {line}")
            continue
        base_path, suffix = line.split(' -', 1)

        # Handle MULTIPLE or single bval
        if suffix == 'MULTIPLE':
            # Look inside dwi folder for *_dwi.bval files
            dwi_dir = os.path.join(base_path, 'dwi')
            if not os.path.isdir(dwi_dir):
                print(f"Warning: dwi folder not found at {dwi_dir}, skipping.")
                continue
            bval_files = [f for f in os.listdir(dwi_dir) if f.endswith('_dwi.bval')]
            if not bval_files:
                print(f"Warning: no bval files found in {dwi_dir}, skipping.")
                continue
            for bval_file in bval_files:
                bval_path = os.path.join(dwi_dir, bval_file)
                sub, ses, run = parse_sub_ses_run_from_path(bval_path)
                if not sub:
                    print(f"Warning: Could not parse subject/session/run from {bval_file}, skipping.")
                    continue

                bval_wc = word_count_in_file(bval_path)
                if bval_wc < BVAL_NEEDED:
                    # Skip low bval scans
                    continue

                # Compose dwi filename expected
                # Remove _bval suffix, add _dwi.nii.gz
                dwi_file = bval_file.replace('.bval', '.nii.gz').replace('_bval', '_dwi')
                dwi_path = os.path.join(dwi_dir, dwi_file)

                # Prepare dictionary for this scan
                row = {
                    'subject': sub,
                    'session': ses,
                    'run': run,
                    'bval_word_count': bval_wc,
                    'dwi_file': dwi_file,
                    'dwi_path': dwi_path
                }

                # Check denoised failure
                if check_denoised_flag:
                    deriv_preproc_dir = os.path.join(DERIVATIVES_PATH, sub, f"ses-{ses}", "preproc")
                    denoised_file = f"{sub}_ses-{ses}" + (f"_run-{run}" if run != '--' else "") + "_dwi_denoised.nii.gz"
                    denoised_path = os.path.join(deriv_preproc_dir, denoised_file)
                    denoised_exists = os.path.isfile(denoised_path)

                    # Log file for denoise job
                    log_file = f"{sub}_ses-{ses}" + (f"_run-{run}" if run != '--' else "") + "_job-01_denoise.out"
                    log_path = os.path.join(LOG_PATH, log_file)
                    failed_in_log = check_log_for_failure(log_path)

                    row['denoised_failed'] = (bval_wc > BVAL_NEEDED) and (failed_in_log or not denoised_exists)

                # Check rmgibbs failure
                if check_rmgibbs_flag:
                    # rmgibbs job log filename
                    log_file = f"{sub}_ses-{ses}" + (f"_run-{run}" if run != '--' else "") + "_job-02_rmgibbs.out"
                    log_path = os.path.join(LOG_PATH, log_file)
                    failed_in_log = check_log_for_failure(log_path)
                    row['rmgibbs_failed'] = failed_in_log

                # Placeholder checks for eddy and eddyqc
                # These would need your actual implementation
                if check_eddy_flag:
                    # Implement your logic here for eddy_failed
                    row['eddy_failed'] = False  # Replace with real check

                if check_eddyqc_flag:
                    # Implement your logic here for eddyqc_failed
                    row['eddyqc_failed'] = False  # Replace with real check

                rows.append(row)

        else:
            # single bval file path after base path, e.g. sub-14921x820_ses-SCAP1_run-01_dwi.bval
            bval_rel_path = suffix
            bval_path = os.path.join(base_path, 'dwi', bval_rel_path)
            if not os.path.isfile(bval_path):
                print(f"Warning: Specified bval file {bval_path} does not exist, skipping.")
                continue

            sub, ses, run = parse_sub_ses_run_from_path(bval_path)
            if not sub:
                print(f"Warning: Could not parse subject/session/run from {bval_path}, skipping.")
                continue

            bval_wc = word_count_in_file(bval_path)
            if bval_wc < BVAL_NEEDED:
                continue

            dwi_file = bval_rel_path.replace('.bval', '.nii.gz').replace('_bval', '_dwi')
            dwi_path = os.path.join(base_path, 'dwi', dwi_file)

            row = {
                'subject': sub,
                'session': ses,
                'run': run,
                'bval_word_count': bval_wc,
                'dwi_file': dwi_file,
                'dwi_path': dwi_path
            }

            # Checks same as above
            if check_denoised_flag:
                deriv_preproc_dir = os.path.join(DERIVATIVES_PATH, sub, f"ses-{ses}", "preproc")
                denoised_file = f"{sub}_ses-{ses}" + (f"_run-{run}" if run != '--' else "") + "_dwi_denoised.nii.gz"
                denoised_path = os.path.join(deriv_preproc_dir, denoised_file)
                denoised_exists = os.path.isfile(denoised_path)

                log_file = f"{sub}_ses-{ses}" + (f"_run-{run}" if run != '--' else "") + "_job-01_denoise.out"
                log_path = os.path.join(LOG_PATH, log_file)
                failed_in_log = check_log_for_failure(log_path)

                row['denoised_failed'] = (bval_wc > BVAL_NEEDED) and (failed_in_log or not denoised_exists)

            if check_rmgibbs_flag:
                log_file = f"{sub}_ses-{ses}" + (f"_run-{run}" if run != '--' else "") + "_job-02_rmgibbs.out"
                log_path = os.path.join(LOG_PATH, log_file)
                failed_in_log = check_log_for_failure(log_path)
                row['rmgibbs_failed'] = failed_in_log

            if check_eddy_flag:
                row['eddy_failed'] = False  # placeholder

            if check_eddyqc_flag:
                row['eddyqc_failed'] = False  # placeholder

            rows.append(row)

    # Determine which failure columns are present
    failure_cols = [col for col in ['eddyqc_failed', 'eddy_failed', 'rmgibbs_failed', 'denoised_failed'] if any(col in r for r in rows)]

    def sort_key(r):
        # Compose tuple of flags in order, default False if not present
        flags = tuple(r.get(col, False) for col in failure_cols)
        # Add bval_word_count last for descending sort
        return flags + (r.get('bval_word_count', 0),)

    # Sort with True first in flags and bval_word_count descending
    # Because True > False, reverse=True puts True flags first and largest bval_word_count last,
    # so invert bval_word_count by multiplying by -1 for correct descending order
    def final_sort_key(r):
        flags = tuple(r.get(col, False) for col in failure_cols)
        bval = r.get('bval_word_count', 0)
        return flags + (-bval,)

    rows.sort(key=final_sort_key, reverse=True)

    # Write CSV
    if rows:
        fieldnames = ['subject', 'session', 'run', 'dwi_file', 'dwi_path', 'bval_word_count'] + failure_cols
    else:
        fieldnames = ['subject', 'session', 'run', 'dwi_file', 'dwi_path', 'bval_word_count']

    with open(OUTPUT_CSV, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Report written to {OUTPUT_CSV}")
    print(f"Total scans: {len(rows)}")
    print(f"Failure columns sorted by: {failure_cols if failure_cols else 'None'}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: failurechecks.py [--denoised] [--rmgibbs] [--eddy] [--eddyqc] [--all]")
        sys.exit(1)
    main()

