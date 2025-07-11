import os
import pandas as pd
import re

# Base directory containing the derivative data
base_dir = '/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/derivatives/'

# Expected columns for QC regions
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

dataframes = []
skipped_files = []

for root, dirs, files in os.walk(base_dir):
    if os.path.basename(root) == 't1_qc':
        for file in files:
            if re.match(r'qc(?:_run-\d+)?\.csv$', file):
                file_path = os.path.join(root, file)
                try:
                    df = pd.read_csv(file_path)

                    # Remove repeated header rows
                    df = df[df.iloc[:, 0] != "subject"]

                    # Skip if the file ends up empty
                    if df.empty or df.isna().all().all():
                        skipped_files.append(file_path)
                        continue

                    # Assign proper column names
                    df.columns = ['subject'] + region_cols

                    # Extract subject/session IDs from folder path
                    parts = root.split(os.sep)
                    subject_id = next((p for p in parts if p.startswith("sub-")), None)
                    session_id = next((p for p in parts if p.startswith("ses-")), None)

                    # Extract run number from filename (defaults to 0 if not present)
                    run_match = re.search(r'run-(\d+)', file)
                    run_number = int(run_match.group(1)) if run_match else 0

                    # Insert metadata columns
                    df.insert(0, 'subject_id', subject_id)
                    df.insert(1, 'session_id', session_id)
                    df.insert(2, 'qc_file', file)
                    df.insert(3, 'run_number', run_number)  # New column for sorting

                    dataframes.append(df)

                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    skipped_files.append(file_path)

# Filter out any empty or invalid DataFrames (defensive coding)
dataframes = [df for df in dataframes if not df.empty and not df.isna().all().all()]

if not dataframes:
    print("No valid QC CSV files found.")
    exit()

# Combine all valid QC DataFrames
combined_df = pd.concat(dataframes, ignore_index=True)

# Sort by subject_id, session_id, then run_number
combined_df.sort_values(by=['subject_id', 'session_id', 'run_number'], inplace=True)

# Drop 'run_number' column if you don't want it in the final CSV
combined_df.drop(columns=['run_number'], inplace=True)

# Output path
output_csv = 'subject_t1_qc.csv'
combined_df.to_csv(output_csv, index=False)
print(f"Combined QC CSV saved to: {os.path.abspath(output_csv)}")

# Report skipped files
if skipped_files:
    print(f"\nSkipped {len(skipped_files)} files due to errors or empty content:")
    for path in skipped_files:
        print(f"  - {path}")

# Print total unique subjects processed
unique_subjects = combined_df['subject_id'].nunique()
print(f"\nTotal unique subjects processed: {unique_subjects}")

