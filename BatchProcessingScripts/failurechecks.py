import os
import re
import csv
import argparse

LOG_PATH = "/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/misc/logs"
SUBJECTS_FILE = "compatible_bval_subjects.txt"
BVAL_NEEDED = 30
OUTPUT_CSV = "denoise_failure_dwi_report.csv"

def word_count_in_file(filepath):
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            return len(content.split())
    except FileNotFoundError:
        return 0

def check_log_for_failure(log_path):
    if not os.path.isfile(log_path):
        return False
    with open(log_path, 'r', errors='ignore') as f:
        content = f.read()
    return 'failed' in content.lower()

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

                run_id = re.sub(r'_dwi\.nii\.gz$', '', dwi_file)
                log_name = re.sub(r'_run-', '_job-01_denoise_run-', run_id) + '.out'
                log_path = os.path.join(LOG_PATH, log_name)

                failed_in_log = check_log_for_failure(log_path)
                truly_failed = bval_wc > BVAL_NEEDED and failed_in_log

                m = re.match(r'(sub-[^_]+_ses-[^_]+)_run-(\d+)', run_id)
                if m:
                    subject_ses = m.group(1)
                    run_num = m.group(2)
                else:
                    subject_ses = run_id
                    run_num = ''

                rows.append({
                    'subject_ses': subject_ses,
                    'run': run_num,
                    'dwi_file': dwi_file,
                    'bval_word_count': bval_wc,
                    'log_found': os.path.isfile(log_path),
                    'failed_in_log': failed_in_log,
                    'truly_failed': truly_failed
                })

    # Sort so that truly_failed = True come first
    rows.sort(key=lambda x: x['truly_failed'], reverse=True)

    with open(OUTPUT_CSV, 'w', newline='') as csvfile:
        fieldnames = ['subject_ses', 'run', 'dwi_file', 'bval_word_count', 'log_found', 'failed_in_log', 'truly_failed']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    print(f"Report written to {OUTPUT_CSV}")
    print(f"Total scans: {len(rows)}")
    print(f"Truly failed scans: {sum(r['truly_failed'] for r in rows)}")

def main():
    parser = argparse.ArgumentParser(description="Run various failure checks on DWI scans and logs.")
    parser.add_argument('--checkdenoised', action='store_true', help='Run the denoised failure check')

    args = parser.parse_args()

    if args.checkdenoised:
        check_denoised()
    else:
        print("No check flag provided. Use --checkdenoised to run the denoised check.")

if __name__ == '__main__':
    main()

