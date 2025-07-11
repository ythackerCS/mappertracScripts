import os
import pandas as pd
import re

base_dir = '/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/derivatives/'

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

for root, dirs, files in os.walk(base_dir):
    if os.path.basename(root) == 't1_qc':
        for file in files:
            if re.match(r'qc(?:_run-\d+)?\.csv$', file):
                file_path = os.path.join(root, file)
                try:
                    df = pd.read_csv(file_path)

                    # Remove repeated header rows inside files
                    df = df[df.iloc[:, 0] != "subject"]

                    # Set proper column names
                    df.columns = ['subject'] + region_cols

                    # Extract subject and session from folder path
                    parts = root.split(os.sep)
                    subject_id = next((p for p in parts if p.startswith("sub-")), None)
                    session_id = next((p for p in parts if p.startswith("ses-")), None)

                    # Insert metadata columns
                    df.insert(0, 'subject_id', subject_id)
                    df.insert(1, 'session_id', session_id)
                    df.insert(2, 'qc_file', file)

                    dataframes.append(df)

                except Exception as e:
                    print(f"Error reading {file_path}: {e}")

if not dataframes:
    print("No QC CSV files found.")
    exit()

combined_df = pd.concat(dataframes, ignore_index=True)

# Save combined CSV in current directory
output_csv = 'subject_t1_qc.csv'
combined_df.to_csv(output_csv, index=False)
print(f"Combined QC CSV saved to: {os.path.abspath(output_csv)}")

