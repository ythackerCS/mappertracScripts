import os
import pandas as pd
from collections import Counter

csv_dir = '/ceph/chpc/shared/shinjini_kundu_group/SFARI_UCSF/Simons_Searchlight_Phase1_16p11.2_Dataset_v11.0'

family_type_counts = Counter()

for filename in os.listdir(csv_dir):
    if filename.endswith('.csv'):
        filepath = os.path.join(csv_dir, filename)
        try:
            df = pd.read_csv(filepath)
        except Exception as e:
            print(f"Skipping {filename} due to read error: {e}")
            continue

        # Find family_type column case-insensitive
        cols_lower = [c.lower() for c in df.columns]
        if 'family_type' not in cols_lower:
            print(f"Skipping {filename}: no Family_Type column")
            continue

        family_type_col = df.columns[cols_lower.index('family_type')]

        # Drop NA and count occurrences
        values = df[family_type_col].dropna().astype(str)
        family_type_counts.update(values)

# Print results sorted by count descending
for fam_type, count in family_type_counts.most_common():
    print(f"{count}\t{fam_type}")

