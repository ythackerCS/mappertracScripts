#!/usr/bin/env python3
import os
import re
import csv

# Constants
SUBJECTS_FILE = "compatible_bval_subjects.txt"
LOG_PATH = "/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/misc/logs"
DERIVATIVES_PATH = "/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/derivatives"
OUTPUT_CSV = "denoised_failure_report.csv"
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

def check_denoised():
    rows = []
    with open(SUBJECTS_FILE, 'r') as f:
        for line in f:
            line = line.strip()
            if '-MULTIPLE' not in line:
                continue

            base_path = line.split(' -MULTIPLE')[0]
            dwi_dir = os.path.join(base_path, 'dwi')

            if not os.path.isdir(dwi_dir):
                print(f"Warning: directory {dwi_dir} not found, skipping.")
                continue

            dwi_files = [f for f in os.listdir(dwi_dir) if f.endswith('_dwi.nii.gz')]
            if not dwi_files:
                print(f"No DWI scans found in {dwi_dir}")
                continue

            for dwi_file in dwi_files:
                bval_file = dwi_file.replace('_dwi.nii.gz', '_dwi.bval')
                bval_path = os.path.join(dwi_dir, bval_file)
                bval_wc = word_count_in_file(bval_path)

                run_match = re.search(r'run-(\d+)', dwi_file)
                run_num = run_match.group(1) if run_match else ''

                log_name = re.sub(r'_run-', '_job-01_denoise_run-', dwi_file.replace('_dwi.nii.gz', '')) + '.out'
                log_path = os.path.join(LOG_PATH, log_name)

                failed_in_log = check_log_for_failure(log_path)

                # Parse subject and session from dwi_dir path or fallback to filename
                dwi_dir_parts = dwi_dir.rstrip('/').split('/')
                sub_ses_part = dwi_dir_parts[-2] if len(dwi_dir_parts) >= 2 else ""
                m_sub_ses = re.match(r'(sub-[^_]+)_ses-([^_]+)', sub_ses_part)
                if m_sub_ses:
                    sub = m_sub_ses.group(1)
                    ses = f"ses-{m_sub_ses.group(2)}"
                else:
                    m_file = re.match(r'(sub-[^_]+)_ses-([^_]+)_run-\d+', dwi_file)
                    if m_file:
                        sub = m_file.group(1)
                        ses = f"ses-{m_file.group(2)}"
                    else:
                        sub = None
                        ses = None

                denoised_exists = False
                if sub and ses:
                    deriv_preproc_dir = os.path.join(DERIVATIVES_PATH, sub, ses, "preproc")
                    denoised_filename = f"{sub}_{ses}_run-{run_num}_dwi_denoised.nii.gz"
                    denoised_path = os.path.join(deriv_preproc_dir, denoised_filename)
                    denoised_exists = os.path.isfile(denoised_path)

                truly_failed = (bval_wc > BVAL_NEEDED) and (failed_in_log or not denoised_exists)

                rows.append({
                    'dwi_path': dwi_dir,
                    'run': run_num,
                    'dwi_file': dwi_file,
                    'bval_word_count': bval_wc,
                    'log_found': os.path.isfile(log_path),
                    'failed_in_log': failed_in_log,
                    'denoised_exists': denoised_exists,
                    'truly_failed': truly_failed
                })

    # Sort by truly_failed (True first), then bval_word_count descending
    rows.sort(key=lambda x: (x['truly_failed'], x['bval_word_count']), reverse=True)

    fieldnames = ['dwi_path', 'run', 'dwi_file', 'bval_word_count', 'log_found', 'failed_in_log', 'denoised_exists', 'truly_failed']
    with open(OUTPUT_CSV, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Report written to {OUTPUT_CSV}")
    print(f"Total scans: {len(rows)}")
    print(f"Truly failed scans: {sum(r['truly_failed'] for r in rows)}")

def main():
    import sys
    if '--checkdenoised' in sys.argv:
        check_denoised()
    else:
        print("Usage: failure_checks.py --checkdenoised")

if __name__ == "__main__":
    main()

