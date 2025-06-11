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

# Step 2: Go through CSV files, starting with the prioritized one
csv_dir = '/ceph/chpc/shared/shinjini_kundu_group/SFARI_UCSF/Simons_Searchlight_Phase1_16p11.2_Dataset_v11.0'
output_filename = 'matched_family_types_from_all_csvs.csv'
results = []

# Create a sorted list of files with priority given to 'svip_subjects_16p11.2.csv'
all_csv_files = sorted(
    os.listdir(csv_dir),
    key=lambda f: (f != 'svip_subjects_16p11.2.csv', f)  # Prioritize this specific file
)

for filename in all_csv_files:
    if not filename.endswith('.csv') or filename == output_filename:
        continue

    csv_path = os.path.join(csv_dir, filename)

    try:
        df = pd.read_csv(csv_path)
    except Exception as e:
        print(f"Skipping file {filename} due to error: {e}")
        continue

    # Normalize column names
    df.columns = df.columns.str.lower()
    id_columns = [col for col in ['individual', 'sfari_id'] if col in df.columns]
    
    if not id_columns or 'family_type' not in df.columns:
        print(f"Skipping {filename} (missing required ID and/or family_type columns)")
        continue

    # Normalize ID columns by stripping dashes and whitespace
    for id_col in id_columns:
        df[id_col] = df[id_col].astype(str).str.replace('-', '', regex=False).str.strip()

    for eid in extracted_ids:
        # Skip if already matched
        if any(r['Extracted_ID'] == eid for r in results):
            continue

        # Try matching against any valid ID column
        match_row = None
        for id_col in id_columns:
            match = df[df[id_col].apply(lambda x: x in eid)]
            if not match.empty:
                match_row = match.iloc[0]
                matched_col_value = match_row[id_col]
                break

        if match_row is not None:
            results.append({
                'Extracted_ID': eid,
                'Matched_Individual': matched_col_value,
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

# Step 5: Print unique Family_Type values and counts (including 'Not Found')
print("\nFamily_Type counts (including 'Not Found'):")
family_type_counts = results_df['Family_Type'].value_counts()
print(family_type_counts)
