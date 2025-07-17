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

def check_gibbs_failure(sub, ses, run):
    """
    Checks if the rmgibbs log for job-02 failed for given subject/session/run.
    Return True if failed, False otherwise.
    """
    # Compose log filename for job-02 rmgibbs run
    run_part = f"_run-{run}" if run != "--" else ""
    log_filename = f"{sub}_{ses}_job-02_rmgibbs{run_part}.out"
    log_path = os.path.join(LOG_PATH, log_filename)
    return check_log_for_failure(log_path)

def check_denoised_failure(sub, ses, run):
    """
    Checks if denoised file exists and if job-01 denoise log failed.
    Returns tuple (failed_in_log, denoised_exists)
    """
    run_part = f"_run-{run}" if run != "--" else ""
    denoise_log_filename = f"{sub}_{ses}_job-01_denoise{run_part}.out"
    denoise_log_path = os.path.join(LOG_PATH, denoise_log_filename)
    failed_in_log = check_log_for_failure(denoise_log_path)

    deriv_preproc_dir = os.path.join(DERIVATIVES_PATH, sub, ses, "preproc")
    denoised_filename = f"{sub}_{ses}{run_part}_dwi_denoised.nii.gz"
    denoised_path = os.path.join(deriv_preproc_dir, denoised_filename)
    denoised_exists = os.path.isfile(denoised_path)

    return failed_in_log, denoised_exists

def parse_sub_ses_run_from_path(dwi_dir, filename):
    """
    Parse subject, session, and run from folder path if possible,
    else from filename, else run='--'.
    """
    # Try folder path first: expect .../sub-XXX/ses-YYY/
    parts = dwi_dir.rstrip('/').split('/')
    if len(parts) >= 2:
        sub_ses_part = parts[-2]
        m = re.match(r'(sub-[^_]+)_ses-([^_]+)', sub_ses_part)
        if m:
            sub = m.group(1)
            ses = f"ses-{m.group(2)}"
            # Parse run from filename if present
            run_match = re.search(r'run-(\d+)', filename)
            run = run_match.group(1) if run_match else "--"
            return sub, ses, run

    # Fallback: try parsing from filename only
    m_file = re.match(r'(sub-[^_]+)_ses-([^_]+)(?:_run-(\d+))?', filename)
    if m_file:
        sub = m_file.group(1)
        ses = f"ses-{m_file.group(2)}"
        run = m_file.group(3) if m_file.group(3) else "--"
        return sub, ses, run

    # If all else fails
    return None, None, "--"

def main():
    # Flags
    check_denoise_flag = False
    check_gibbs_flag = False

    args = sys.argv[1:]
    if '--all' in args:
        check_denoise_flag = True
        check_gibbs_flag = True
    else:
        if '--checkdenoised' in args:
            check_denoise_flag = True
        if '--checkgibbs' in args:
            check_gibbs_flag = True

    if not (check_denoise_flag or check_gibbs_flag):
        print("Usage: failure_checks.py [--checkdenoised] [--checkgibbs] [--all]")
        sys.exit(1)

    rows = []
    total_scans = 0

    with open(SUBJECTS_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            # We only handle lines with -MULTIPLE, for which we scan folder contents
            if '-MULTIPLE' not in line:
                continue

            base_path = line.split(' -MULTIPLE')[0]
            dwi_dir = os.path.join(base_path, 'dwi')

            if not os.path.isdir(dwi_dir):
                print(f"Warning: dwi directory not found at {dwi_dir}, skipping.")
                continue

            dwi_files = [file for file in os.listdir(dwi_dir) if file.endswith('_dwi.nii.gz')]
            if not dwi_files:
                print(f"No DWI scans found in {dwi_dir}, skipping.")
                continue

            for dwi_file in dwi_files:
                bval_file = dwi_file.replace('_dwi.nii.gz', '_dwi.bval')
                bval_path = os.path.join(dwi_dir, bval_file)
                bval_wc = word_count_in_file(bval_path)
                if bval_wc == 0:
                    # No valid bval, skip
                    continue

                if bval_wc < BVAL_NEEDED:
                    # Skip bvals with insufficient volumes
                    continue

                total_scans += 1

                sub, ses, run = parse_sub_ses_run_from_path(dwi_dir, dwi_file)

                if sub is None or ses is None:
                    print(f"Warning: Could not parse subject/session from {dwi_file} in {dwi_dir}, skipping.")
                    continue

                row = {
                    'subject': sub,
                    'session': ses,
                    'run': run,
                    'dwi_path': dwi_dir,
                    'dwi_file': dwi_file,
                    'bval_word_count': bval_wc,
                }

                if check_denoise_flag:
                    failed_in_log, denoised_exists = check_denoised_failure(sub, ses, run)
                    row.update({
                        'denoised_failed_in_log': failed_in_log,
                        'denoised_exists': denoised_exists,
                        'denoised_failed': (failed_in_log or not denoised_exists)
                    })
                else:
                    row.update({
                        'denoised_failed_in_log': None,
                        'denoised_exists': None,
                        'denoised_failed': None
                    })

                if check_gibbs_flag:
                    rmgibbs_failed = check_gibbs_failure(sub, ses, run)
                    row['rmgibbs_failed'] = rmgibbs_failed
                else:
                    row['rmgibbs_failed'] = None

                rows.append(row)

    # Sort: denoised_failed True first, then bval_word_count desc
    if check_denoise_flag:
        rows.sort(key=lambda x: (x['denoised_failed'] if x['denoised_failed'] is not None else False, x['bval_word_count']), reverse=True)
    else:
        # sort by bval_word_count desc
        rows.sort(key=lambda x: x['bval_word_count'], reverse=True)

    # Write CSV
    fieldnames = ['subject', 'session', 'run', 'dwi_path', 'dwi_file', 'bval_word_count']
    if check_denoise_flag:
        fieldnames += ['denoised_failed_in_log', 'denoised_exists', 'denoised_failed']
    if check_gibbs_flag:
        fieldnames.append('rmgibbs_failed')

    with open(OUTPUT_CSV, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    # Summary
    print(f"Total scans processed (bval_word_count >= {BVAL_NEEDED}): {total_scans}")
    if check_denoise_flag:
        denoised_failed_count = sum(1 for r in rows if r.get('denoised_failed'))
        print(f"Scans with denoised failure: {denoised_failed_count}")
    if check_gibbs_flag:
        rmgibbs_failed_count = sum(1 for r in rows if r.get('rmgibbs_failed'))
        print(f"Scans with rmgibbs failure: {rmgibbs_failed_count}")

if __name__ == "__main__":
    main()
