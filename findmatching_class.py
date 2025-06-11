import os
import re
import pandas as pd

# Step 1: Extract IDs from the txt file
txt_path = 'compatible_bval_subjects.txt'
extracted_ids = []

with open(txt_path, 'r') as file:
    for line in file:
        match = re.search(r'sub-([^/]+)', line)
        if match:
            extracted_ids.append(match.group(1))

print(f"Total extracted IDs: {len(extracted_ids)}")

# Step 2: Go through every CSV in the folder
csv_dir = '/ceph/chpc/shared/shinjini_kundu_group/SFARI_UCSF/Simons_Searchlight_Phase1_16p11.2_Dataset_v11.0'
output_filename = 'matched_family_types_from_all_csvs.csv'
results = []

for filename in os.listdir(csv_dir):
    if filename.endswith('.csv'):
        if filename == output_filename:
            print(f"Skipping output file {filename}")
            continue

        csv_path = os.path.join(csv_dir, filename)

        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            print(f"Skipping file {filename} due to error: {e}")
            continue

        # Normalize column names
        df.columns = df.columns.str.lower()

        if 'individual' not in df.columns or 'family_type' not in df.columns:
            print(f"Skipping {filename} (missing required columns)")
            continue

        # Remove dashes from individual values
        df['individual'] = df['individual'].astype(str).str.replace('-', '', regex=False).str.strip()

        for eid in extracted_ids:
            # Skip if already matched
            if any(r['Extracted_ID'] == eid for r in results):
                continue

            matches = df[df['individual'].apply(lambda x: x in eid)]

            if not matches.empty:
                match_row = matches.iloc[0]
                results.append({
                    'Extracted_ID': eid,
                    'Matched_Individual': match_row['individual'],
                    'Family_Type': match_row['family_type'],
                    'Source_File': filename
                })

# Step 3: Add IDs without any match as Not Found
matched_ids = set(r['Extracted_ID'] for r in results)
for eid in extracted_ids:
    if eid not in matched_ids:
        results.append({
            'Extracted_ID': eid,
            'Matched_Individual': 'Not Found',
            'Family_Type': 'Not Found',
            'Source_File': ''
        })

# Step 4: Output results
results_df = pd.DataFrame(results)
results_df.to_csv(output_filename, index=False)
print("Final Results:")
print(results_df)

