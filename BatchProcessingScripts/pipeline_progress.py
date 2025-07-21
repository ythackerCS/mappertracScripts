import os
import csv
import argparse
import sys
import json 


# Defaults
output_file = "pipeline_progress.csv"
bval_needed = 30
data_root_default = "/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/sourcedata"
log_dir_default = "/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/misc/logs/job-03_eddyqc"
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
    parser.add_argument("--rmgibbs", action='store_true', help="Check rmgibbs logs and update CSV")
    parser.add_argument('--eddy', action='store_true', help='Update Eddy status in the CSV')
    parser.add_argument('--eddyqc', action='store_true', help='Run EddyQC status update')

    return parser.parse_args()

def print_usage():
    print("Usage: Provide at least one of --getsubjects, --denoise, or --rmgibbs flags.")
    print("Example:")
    print("  python script.py --getsubjects")
    print("  python script.py --denoise")
    print("  python script.py --rmgibbs")
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

def update_rmgibbs_status(args):
    if not os.path.exists(args.output):
        print(f"Error: CSV file '{args.output}' not found. Run with --getsubjects first.")
        sys.exit(1)

    # Load CSV and check for required columns
    with open(args.output, 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = [name.strip() for name in reader.fieldnames]
        rows = [row for row in reader]

    # Check for required columns from previous stages
    if 'Denoised_Log' not in fieldnames or 'Denoised_Status' not in fieldnames:
        print("Error: CSV is missing required columns: 'Denoised_Log' and/or 'Denoised_Status'.")
        print("Please run the script with --denoise first before running --rmgibbs.")
        sys.exit(1)

    # Add columns if missing
    if 'Rmgibbs_Log' not in fieldnames:
        fieldnames.append('Rmgibbs_Log')
    if 'Rmgibbs_Status' not in fieldnames:
        fieldnames.append('Rmgibbs_Status')

    for idx, row in enumerate(rows):
        subject = row['Subject']
        session = row['Session']
        run = row['Run']

        # Default values
        row['Rmgibbs_Log'] = row.get('Rmgibbs_Log', 'NO_LOG')
        row['Rmgibbs_Status'] = row.get('Rmgibbs_Status', 'FALSE')

        # Determine log filename
        run_suffix = run if run else "norun"
        log_file = os.path.join(args.log_dir, f"{subject}_{session}_job-02_rmgibbs_{run_suffix}.out")

        # Base filename for checking denoised output
        if run:
            denoised_filename = f"{subject}_{session}_{run}_dwi_denoised_rmgibbs.nii.gz"
        else:
            denoised_filename = f"{subject}_{session}_dwi_dwi_denoised_rmgibbs.nii.gz"
        denoised_path = os.path.join(args.derivatives_dir, subject, session, 'preproc', denoised_filename)

        # Check log content
        if os.path.exists(log_file):
            with open(log_file, 'r') as lf:
                content = lf.read()

                if "FAIL" in content:
                    row['Rmgibbs_Log'] = "FAIL"
                    row['Rmgibbs_Status'] = "FALSE"
                elif "COMPLETE" in content:
                    row['Rmgibbs_Log'] = "COMPLETE"
                    if os.path.exists(denoised_path):
                        row['Rmgibbs_Status'] = "TRUE"
                    else:
                        row['Rmgibbs_Status'] = "FALSE"
                else:
                    row['Rmgibbs_Log'] = "IN_PROGRESS"
                    row['Rmgibbs_Status'] = "FALSE"
        else:
            row['Rmgibbs_Log'] = "NO_LOG"
            row['Rmgibbs_Status'] = "FALSE"

        # Limit in test mode
        if args.test and idx >= 10:
            break

    # Write updated CSV
    with open(args.output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return rows

def update_eddy_status(args):
    if not os.path.exists(args.output):
        print(f"Error: CSV file '{args.output}' not found. Run with --getsubjects first.")
        sys.exit(1)

    # Load CSV and check for required columns
    with open(args.output, 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = [name.strip() for name in reader.fieldnames]
        rows = [row for row in reader]

    # Check for required columns from previous stages
    required_cols = ['Denoised_Log', 'Denoised_Status', 'Rmgibbs_Log', 'Rmgibbs_Status']
    missing_cols = [col for col in required_cols if col not in fieldnames]

    if missing_cols:
        print(f"Error: CSV is missing required columns: {', '.join(missing_cols)}.")
        print("Please run the script with --denoise and --rmgibbs first before running --eddy.")
        sys.exit(1)

    # Add columns if missing
    if 'Eddy_Log' not in fieldnames:
        fieldnames.append('Eddy_Log')
    if 'Eddy_Status' not in fieldnames:
        fieldnames.append('Eddy_Status')

    for idx, row in enumerate(rows):
        subject = row['Subject']
        session = row['Session']
        run = row.get('Run', '')  # some rows may not have Run, but we try to be safe

        # Default values
        row['Eddy_Log'] = row.get('Eddy_Log', 'NO_LOG')
        row['Eddy_Status'] = row.get('Eddy_Status', 'FALSE')

        # Determine log filename
        run_suffix = run if run else "norun"
        log_file = os.path.join(args.log_dir, f"{subject}_{session}_job-03_eddy_{run_suffix}.out")

        # Base filename for checking denoised rmgibbs output
        if run:
            rmgibbs_filename = f"{subject}_{session}_{run}_denoised_rmgibbs_eddy_brain.nii.gz"
        else:
            rmgibbs_filename = f"{subject}_{session}_denoised_rmgibbs_eddy_brain.nii.gz"
        rmgibbs_path = os.path.join(args.derivatives_dir, subject, session, 'preproc', rmgibbs_filename)

        # Check log content with unicode error safeguard
        if os.path.exists(log_file):
            try:
                with open(log_file, 'r') as lf:
                    content = lf.read().lower()  # case insensitive
            except UnicodeDecodeError:
                print(f"Warning: Log file '{log_file}' contains unusual unicode characters, reading with ignore errors.")
                row['Eddy_Log'] = "RERUN_CHPCERROR"
                row['Eddy_Status'] = "FALSE"
                continue  # skip the rest of the loop for this row

            if "skipping" in content:
                row['Eddy_Log'] = "SKIPPED"
                row['Eddy_Status'] = "FALSE"
            elif "filenotfounderror" in content:
                row['Eddy_Log'] = "FILENOTFOUND"
                row['Eddy_Status'] = "FALSE"
            elif "binary brain mask saved" in content or "found post-eddy brain mask" in content:
                row['Eddy_Log'] = "COMPLETE"
                if os.path.exists(rmgibbs_path):
                    row['Eddy_Status'] = "TRUE"
                else:
                    row['Eddy_Status'] = "FALSE"
            else:
                row['Eddy_Log'] = "IN_PROGRESS"
                row['Eddy_Status'] = "FALSE"
        else:
            row['Eddy_Log'] = "NO_LOG"
            row['Eddy_Status'] = "FALSE"

        # Limit in test mode
        if args.test and idx >= 10:
            break

    # Write updated CSV
    with open(args.output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return rows


def update_eddyqc_status(args):
    import os
    import sys
    import csv
    import json

    if not os.path.exists(args.output):
        print(f"Error: CSV file '{args.output}' not found. Run with --getsubjects first.")
        sys.exit(1)

    with open(args.output, 'r') as f:
        reader = csv.DictReader(f)
        fieldnames = [name.strip() for name in reader.fieldnames]
        rows = [row for row in reader]

    if 'Eddy_Log' not in fieldnames or 'Eddy_Status' not in fieldnames:
        print("Error: CSV is missing required columns: 'Eddy_Log' and/or 'Eddy_Status'.")
        print("Please run the script with --eddy first before running --eddyqc.")
        sys.exit(1)

    if 'Eddyqc_Log' not in fieldnames:
        fieldnames.append('Eddyqc_Log')
    if 'Eddyqc_Status' not in fieldnames:
        fieldnames.append('Eddyqc_Status')

    keys_to_add = [
        "qc_cnr_avg", "qc_cnr_flag", "qc_cnr_std", "qc_field_flag",
        "qc_mot_abs", "qc_mot_rel", "qc_ol_flag",
        "qc_outliers_b", "qc_outliers_pe", "qc_outliers_tot",
        "qc_params_avg", "qc_params_flag", "qc_path",
        "qc_rss_flag", "qc_s2v_params_avg_std", "qc_s2v_params_flag",
        "qc_vox_displ_std"
    ]

    for key in keys_to_add:
        if key not in fieldnames:
            fieldnames.append(key)

    for idx, row in enumerate(rows):
        subject = row['Subject']
        session = row['Session']
        run = row['Run']

        row['Eddyqc_Log'] = row.get('Eddyqc_Log', 'NO_LOG')
        row['Eddyqc_Status'] = row.get('Eddyqc_Status', 'FALSE')

        for key in keys_to_add:
            row[key] = ''

        if run:
            log_file = os.path.join(args.log_dir, f"{subject}_{session}_{run}_job-04_eddyqc.out")
            qc_folder = os.path.join(
                args.derivatives_dir,
                subject,
                session,
                'preproc',
                f"{subject}_{session}_{run}_denoised_rmgibbs_eddy.qc"
            )
        else:
            log_file = os.path.join(args.log_dir, f"{subject}_{session}_job-04_eddyqc_norun.out")
            qc_folder = os.path.join(
                args.derivatives_dir,
                subject,
                session,
                'preproc',
                f"{subject}_{session}_denoised_rmgibbs_eddy.qc"
            )

        # Check if log file exists and update Eddyqc_Log accordingly
        if os.path.exists(log_file):
            with open(log_file, 'r') as lf:
                content = lf.read().lower()

            if "denoised_rmgibbs_eddy does not appear to be a valid eddy output basename" in content:
                row['Eddyqc_Log'] = "MISSING EDDY"
                row['Eddyqc_Status'] = "FALSE"
            elif "fail" in content:
                row['Eddyqc_Log'] = "FAIL"
                row['Eddyqc_Status'] = "FALSE"
            else:
                row['Eddyqc_Log'] = "TRUE"
        else:
            # Log missing but continue to check qc files
            row['Eddyqc_Log'] = "NO_LOG"

        qc_pdf = os.path.join(qc_folder, "qc.pdf")
        qc_json = os.path.join(qc_folder, "qc.json")

        # Always check qc files
        if os.path.exists(qc_pdf) and os.path.exists(qc_json):
            row['Eddyqc_Status'] = "TRUE"
            try:
                with open(qc_json, 'r') as jq:
                    qc_data = json.load(jq)

                for key in keys_to_add:
                    if key in qc_data:
                        value = qc_data[key]
                        if isinstance(value, (list, dict)):
                            value = json.dumps(value)
                        else:
                            value = str(value)
                        row[key] = value

            except Exception as e:
                print(f"Warning: Failed to read or parse qc.json for {subject} {session} run={run}: {e}")
        else:
            # QC files missing, set status false only if not already false due to log errors
            if row['Eddyqc_Status'] != "FALSE":
                row['Eddyqc_Status'] = "FALSE"

        if args.test and idx >= 10:
            break

    with open(args.output, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return rows

def print_csv_filtered(filename, max_rows=10, exclude_prefix="qc_"):
    with open(filename, 'r') as f:
        reader = csv.reader(f)
        rows = list(reader)

    if not rows:
        print("(CSV is empty)")
        return

    header = rows[0]
    data_rows = rows[1:max_rows+1]

    # Find indices of columns to exclude
    exclude_indices = [i for i, col in enumerate(header) if col.startswith(exclude_prefix)]

    # Build filtered header and rows
    filtered_header = [col for i, col in enumerate(header) if i not in exclude_indices]
    filtered_rows = [
        [val for i, val in enumerate(row) if i not in exclude_indices]
        for row in data_rows
    ]

    # Print filtered CSV as table-like text
    print(",".join(filtered_header))
    for row in filtered_rows:
        print(",".join(row))

def main():
    args = parse_args()

    if not (args.getsubjects or args.denoise or args.rmgibbs or args.eddy or args.eddyqc):
        print_usage()
        sys.exit(1)

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
            print("\nCSV Content (Test Mode, excluding qc_ columns):")
            print_csv_filtered(args.output, max_rows=10, exclude_prefix="qc_")

    if args.denoise:
        rows = update_denoise_status(args)

        if args.test:
            rows_to_process = rows[:10]
        else:
            rows_to_process = rows

        passes = sum(1 for r in rows_to_process if r['Denoised_Status'] == 'TRUE')
        fails = sum(1 for r in rows_to_process if r['Denoised_Status'] == 'FALSE')

        print(f"Denoised_Status counts: PASS = {passes}, FAILED = {fails}")

        if args.test:
            print("\nCSV Content (Test Mode - First 10 Rows, excluding qc_ columns):")
            print_csv_filtered(args.output, max_rows=10, exclude_prefix="qc_")

    if args.rmgibbs:
        rows = update_rmgibbs_status(args)

        if args.test:
            rows_to_process = rows[:10]
        else:
            rows_to_process = rows

        passes = sum(1 for r in rows_to_process if r.get('Rmgibbs_Status') == 'TRUE')
        fails = sum(1 for r in rows_to_process if r.get('Rmgibbs_Status') == 'FALSE')

        print(f"Rmgibbs_Status counts: PASS = {passes}, FAILED = {fails}")

        if args.test:
            print("\nCSV Content (Test Mode - First 10 Rows, excluding qc_ columns):")
            print_csv_filtered(args.output, max_rows=10, exclude_prefix="qc_")

    if args.eddy:
        rows = update_eddy_status(args)

        if args.test:
            rows_to_process = rows[:10]
        else:
            rows_to_process = rows

        valid_rows = [
            r for r in rows_to_process
            if r.get('Denoised_Status') == 'TRUE' and r.get('Rmgibbs_Status') == 'TRUE'
        ]

        passes = sum(1 for r in valid_rows if r.get('Eddy_Status') == 'TRUE')
        fails = sum(1 for r in valid_rows if r.get('Eddy_Status') == 'FALSE')

        print(f"Eddy_Status counts (only Denoised and Rmgibbs TRUE rows): PASS = {passes}, FAILED = {fails}")

        if args.test:
            print("\nCSV Content (Test Mode - First 10 Rows, excluding qc_ columns):")
            print_csv_filtered(args.output, max_rows=10, exclude_prefix="qc_")

    if args.eddyqc:
        rows = update_eddyqc_status(args)

        if args.test:
            rows_to_process = rows[:10]
        else:
            rows_to_process = rows

        valid_rows = [r for r in rows_to_process if r.get('Eddy_Status') == 'TRUE']

        passes = sum(1 for r in valid_rows if r.get('Eddyqc_Status') == 'TRUE')
        fails = sum(1 for r in valid_rows if r.get('Eddyqc_Status') == 'FALSE')

        print(f"Eddyqc_Status counts (only Eddy_Status TRUE rows): PASS = {passes}, FAILED = {fails}")

        if args.test:
            print("\nCSV Content (Test Mode - First 10 Rows, excluding qc_ columns):")
            print_csv_filtered(args.output, max_rows=10, exclude_prefix="qc_")


if __name__ == "__main__":
    main()

