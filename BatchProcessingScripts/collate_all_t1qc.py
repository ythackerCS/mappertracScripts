import os
import pandas as pd
import glob
import re

# === CONFIGURATION ===
subject_csv = "output.csv"
sourcedata_dir = "/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/sourcedata"
derivatives_dir = "/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/derivatives"
region_cols = [
    "general white matter",
    "general grey matter",
    "general csf",
    "cerebellum",
    "brainstem",
    "thalamus",
    "putamen+pallidum",
    "hippocampus+amygdala"
]
output_qc_csv = "subject_t1_qc.csv"

# === LOAD SUBJECT LIST ===
try:
    subject_df = pd.read_csv(subject_csv)
    subject_ids = subject_df.iloc[:, 0].dropna().unique()
except Exception as e:
    print(f"Failed to read {subject_csv}: {e}")
    exit(1)

# === PART 1: COUNT t1w.nii.gz FILES ===
t1w_file_count = 0
missing_subjects = []

for subject in subject_ids:
    subject_path = os.path.join(sourcedata_dir, subject)
    
    if os.path.isdir(subject_path):
        matches = glob.glob(os.path.join(subject_path, '**', '*t1w.nii.gz'), recursive=True)
        t1w_file_count += len(matches)
    else:
        missing_subjects.append(subject)

print(f"\nTotal '*t1w.nii.gz' files found: {t1w_file_count}")

if missing_subjects:
    print(f"\nSkipped {len(missing_subjects)} subjects due to missing directories:")
    for subj in missing_subjects:
        print(f"  - {subj}")

# === PART 2: AGGREGATE QC CSV FILES ===
dataframes = []
skipped_files = []

for root, dirs, files in os.walk(derivatives_dir):
    if os.path.basename(root) == 't1_qc':
        for file in files:
            if re.match(r'qc(?:_run-\d+)?\.csv$', file):
                file_path = os.path.join(root, file)
                try:
                    df = pd.read_csv(file_path)

                    # Remove repeated header rows
                    df = df[df.iloc[:, 0] != "subject"]

                    # Skip if the file is empty or all NaN
                    if df.empty or df.isna().all().all():
                        skipped_files.append(file_path)
                        continue

                    # Assign column names
                    df.columns = ['subject'] + region_cols

                    # Extract metadata from path
                    parts = root.split(os.sep)
                    subject_id = next((p for p in parts if p.startswith("sub-")), None)
                    session_id = next((p for p in parts if p.startswith("ses-")), None)

                    # Extract run number
                    run_match = re.search(r'run-(\d+)', file)
                    run_number = int(run_match.group(1)) if run_match else 0

                    # Insert metadata columns
                    df.insert(0, 'subject_id', subject_id)
                    df.insert(1, 'session_id', session_id)
                    df.insert(2, 'qc_file', file)
                    df.insert(3, 'run_number', run_number)

                    dataframes.append(df)

                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    skipped_files.append(file_path)

# Filter out invalid DataFrames
dataframes = [df for df in dataframes if not df.empty and not df.isna().all().all()]

if not dataframes:
    print("No valid QC CSV files found.")
    exit(0)

# Combine, sort, and clean
combined_df = pd.concat(dataframes, ignore_index=True)
combined_df.sort_values(by=['subject_id', 'session_id', 'run_number'], inplace=True)
combined_df.drop(columns=['run_number'], inplace=True)

# Save to CSV
combined_df.to_csv(output_qc_csv, index=False)
print(f"\nCombined QC CSV saved to: {os.path.abspath(output_qc_csv)}")

# Report skipped files
if skipped_files:
    print(f"\nSkipped {len(skipped_files)} QC files due to errors or empty content:")
    for path in skipped_files:
        print(f"  - {path}")

# Report number of unique subjects in QC data
unique_subjects = combined_df['subject_id'].nunique()
print(f"\nTotal unique subjects with QC data: {unique_subjects}")

