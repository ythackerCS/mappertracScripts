import os
import csv
import argparse
import sys
import json 


# Defaults
output_file = "pipeline_progress.csv"
bval_needed = 30
data_root_default = "/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/sourcedata"
log_dir_default = "/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/misc/logs/job-01_denoise"
derivatives_dir_default = "/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/derivatives"

def parse_args():
    parser = argparse.ArgumentParser(description="Process bval files, denoise logs, and generate CSV report")
    parser.add_argument("-o", "--output", type=str, default=output_file, help="Output CSV file name")
    parser.add_argument("-b", "--bvalneeded", type=int, default=bval_needed, help="Min number of bval entries required")
    parser.add_argument("-d", "--data_root", type=str, default=data_root_default, help="Root directory for data")
    parser.add_argument("--log_dir", type=str, default=log_dir_default, help="Directory for denoise logs")
    parser.add_argument("--derivatives_dir", type=str, default=derivatives_dir_default, help="Directory for derivatives")
    parser.add_argument("--test", action='store_true', help="Test mode: limit to first 10 rows and print CSV content")
    parser.add_argument("--getsubjects", action='store_true', help="Scan subjects, sessions, runs and write CSV")
    parser.add_argument("--denoise", action='store_true', help="Check denoise logs and derivatives files and update CSV")
    return parser.parse_args()

def print_usage():
    print("Usage: Provide at least one of --getsubjects or --denoise flags.")
    print("Example:")
    print("  python script.py --getsubjects")
    print("  python script.py --denoise")
    print("  python script.py --getsubjects --test")
    sys.exit(1)

def check_directories(subject_path, session):
    anat_dir = os.path.join(subject_path, session, 'anat')
    dwi_dir = os.path.join(subject_path, session, 'dwi')
    return os.path.isdir(anat_dir), os.path.isdir(dwi_dir), anat_dir, dwi_dir

def check_bval_file(bval_file, min_words):
    if os.path.exists(bval_file):
        with open(bval_file, 'r') as f:
            vals = f.read().split()
            count = len(vals)
            if count < min_words:
                return False, 0
            if len(set(vals)) <= 1:
                return False, 0
            return True, count
    return False, 0

def check_denoised_log(log_file_path):
    if not os.path.exists(log_file_path):
        return "NO_LOG"
    with open(log_file_path, 'r') as f:
        content = f.read()
        if "COMPLETED" in content:
            return "TRUE"
        elif "FAIL" in content:
            return "FAIL"
        elif "PCA denoising can only be performed on 4D arrays" in content:
            return "NOT4D"
    return "NO_LOG"

def check_denoised_file(subject, session, run_number, derivatives_dir):
    if run_number:
        fname = f"{subject}_{session}_{run_number}_dwi_denoised.nii.gz"
    else:
        fname = f"{subject}_{session}_dwi_denoised.nii.gz"
    fpath = os.path.join(derivatives_dir, subject, session, 'preproc', fname)
    return os.path.exists(fpath)

def scan_subjects(args):
    rows = []
    matching_sessions = 0
    total_sessions = 0
    for subject in os.listdir(args.data_root):
        subject_path = os.path.join(args.data_root, subject)
        if not os.path.isdir(subject_path) or not subject.startswith("sub-"):
            continue
        for session in os.listdir(subject_path):
            session_path = os.path.join(subject_path, session)
            if not os.path.isdir(session_path) or not session.startswith("ses-"):
                continue
            anat_exists, dwi_exists, anat_dir, dwi_dir = check_directories(subject_path, session)
            if not anat_exists or not dwi_exists:
                continue
            for bval_file in os.listdir(dwi_dir):
                if bval_file.endswith(".bval"):
                    full_bval_path = os.path.join(dwi_dir, bval_file)
                    valid, count = check_bval_file(full_bval_path, args.bvalneeded)
                    if not valid:
                        continue

                    # Determine run number
                    if '_run-' in bval_file:
                        run_num = bval_file.split('_run-')[-1].split('_dwi.bval')[0]
                        run_num = f"run-{run_num}"
                        base_name = bval_file.replace('.bval', '')  # same base for json
                    else:
                        run_num = ""
                        base_name = bval_file.replace('.bval', '')  # e.g., sub-xxx_ses-yyy_dwi

                    # Look for the corresponding JSON sidecar file
                    json_path = os.path.join(dwi_dir, base_name + '.json')
                    acq_time = ""
                    series_desc = ""
                    if os.path.exists(json_path):
                        try:
                            with open(json_path, 'r') as jf:
                                metadata = json.load(jf)
                                acq_time = metadata.get("AcquisitionTime", "")
                                series_desc = metadata.get("SeriesDescription", "")
                        except json.JSONDecodeError:
                            print(f"Warning: Failed to parse JSON: {json_path}")

                    rows.append([subject, session, run_num, count, acq_time, series_desc])
                    matching_sessions += 1
                    total_sessions += 1

                    # Stop after the first 10 rows if --test is enabled
                    if args.test and len(rows) >= 10:
                        break
            if args.test and len(rows) >= 10:
                break
        if args.test and len(rows) >= 10:
            break
    return rows, matching_sessions, total_sessions

def update_denoise_status(args):
    # Check if the CSV file exists
    if not os.path.exists(args.output):
        print(f"Error: CSV file '{args.output}' not found. Run with --getsubjects first. And perform denoising using batch_processing")
        sys.exit(1)

    # Read the existing CSV file and load its content
    rows = []
    with open(args.output, 'r') as f:
        reader = csv.DictReader(f)
        # Strip whitespace from the column names
        fieldnames = [name.strip() for name in reader.fieldnames]
        rows = [row for row in reader]

    # Add 'Denoised_Log' and 'Denoised_Status' columns if they are missing
    if 'Denoised_Log' not in fieldnames:
        fieldnames.append('Denoised_Log')
    if 'Denoised_Status' not in fieldnames:
        fieldnames.append('Denoised_Status')

    # Loop over rows and update Denoised_Log and Denoised_Status columns
    for idx, row in enumerate(rows):
        # Extract subject, session, and run from the row
        subject = row['Subject']
        session = row['Session']
        run = row['Run']
        
        # Check if the Denoised_Log and Denoised_Status are empty
        if not row.get('Denoised_Log'):  # If Denoised_Log is missing or empty
            row['Denoised_Log'] = "NO_LOG"
        
        if not row.get('Denoised_Status'):  # If Denoised_Status is missing or empty
            row['Denoised_Status'] = "FALSE"

        # Determine log file name based on the presence of a run
        if run and run != "":
            log_file = os.path.join(args.log_dir, f"{subject}_{session}_job-01_denoise_{run}.out")
        else:
            log_file = os.path.join(args.log_dir, f"{subject}_{session}_job-01_denoise_norun.out")  # For no run provided

        # Check the contents of the log file and set the status
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                log_content = f.read()

                # Check for "FAIL"
                if "FAIL" in log_content:
                    row['Denoised_Log'] = "FAIL"
                    row['Denoised_Status'] = "FALSE"

                # Check for "PCA denoising can only be performed on 4D arrays"
                elif "PCA denoising can only be performed on 4D arrays" in log_content:
                    row['Denoised_Log'] = "NOT4D"
                    row['Denoised_Status'] = "FALSE"

                # If the log contains "COMPLETED", check for the denoised file
                elif "COMPLETED" in log_content:
                    if run:
                        file_name = f"{subject}_{session}_{run}_dwi_denoised.nii.gz"
                    else:
                        file_name = f"{subject}_{session}_dwi_denoised.nii.gz"
                    file_path = os.path.join(args.derivatives_dir, subject, session, 'preproc', file_name)

                    # Update Denoised_Status based on file existence
                    if os.path.exists(file_path):
                        row['Denoised_Log'] = "TRUE"
                        row['Denoised_Status'] = "TRUE"
                    else:
                        row['Denoised_Log'] = "COMPLETED_BUT_FILE_MISSING"
                        row['Denoised_Status'] = "FALSE"
                else:
                    row['Denoised_Log'] = "IN_PROGRESS"
                    row['Denoised_Status'] = "FALSE"

        # If --test is enabled, only process the first 10 rows
        if args.test and idx >= 10:
            break

    # Now overwrite the original CSV with the updated rows (no duplicate rows)
    with open(args.output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        # Write the header
        writer.writeheader()

        # Write back the updated rows (no duplicates, same number of rows)
        writer.writerows(rows)

    return rows  # Return rows so you can process them for counts elsewhere

def main():
    args = parse_args()

    if not (args.getsubjects or args.denoise):
        print_usage()

    if args.getsubjects:
        rows, matching_sessions, total_sessions = scan_subjects(args)
        with open(args.output, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Subject", "Session", "Run", "Bval_Word_Count", "AcquisitionTime", "SeriesDescription"])
            for row in rows:
                writer.writerow(row)
        print(f"Using bvalneeded threshold: {args.bvalneeded}")
        print(f"Total matching sessions: {matching_sessions}")
        print(f"Total session folders: {total_sessions}")
        print(f"Rows written to CSV: {len(rows)}")
        print(f"Results written to: {args.output}")
        if args.test:
            print("\nCSV Content (Test Mode):")
            with open(args.output, 'r') as f:
                print(f.read())

    if args.denoise:
        rows = update_denoise_status(args)

        # If --test is enabled, limit to the first 10 rows
        if args.test:
            rows_to_process = rows[:10]
        else:
            rows_to_process = rows

        # Calculate passes and fails based on updated rows (only first 10 rows in test mode)
        passes = sum(1 for r in rows_to_process if r['Denoised_Status'] == 'TRUE')
        fails = sum(1 for r in rows_to_process if r['Denoised_Status'] == 'FALSE')

        print(f"Denoised_Status counts: TRUE = {passes}, FALSE = {fails}")

        if args.test:
            print("\nCSV Content (Test Mode - First 10 Rows):")
            with open(args.output, 'r') as f:
                # Limit output to the first 10 rows
                lines = f.readlines()
                print("".join(lines[:10]))

if __name__ == "__main__":
    main()

