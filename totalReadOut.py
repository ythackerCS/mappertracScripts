import os
import re
import csv
import warnings
import pydicom

# === CONFIGURATION ===
MAX_SUBJECTS_TO_PROCESS = 30  # Limit number of subjects processed
MAX_DCM_FILES_PER_FOLDER = 4  # Limit .dcm files per folder
input_file = "/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/mappertracScripts/compatible_bval_subjects.txt"
unzipped_dir = "/ceph/chpc/shared/shinjini_kundu_group/working/yash/unzippedsubjects"
output_csv = "dicom_time_fields_output.csv"

# === SUPPRESS SPECIFIC WARNINGS ===
warnings.filterwarnings("ignore", message="Invalid value for VR UI")

# === STEP 1: Extract Subject IDs from File ===
def extract_subject_ids(file_path):
    subject_ids = set()
    with open(file_path, 'r') as f:
        for line in f:
            match = re.search(r"sub-(\d+x\d+)", line)
            if match:
                subject_ids.add(match.group(1))
    return subject_ids

# === STEP 2: List all folders in unzipped directory ===
def list_unzipped_folders(directory):
    return [d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d))]

# === STEP 3: Match Subject IDs to Folder Names ===
def match_subjects_to_folders(subject_ids, folders):
    matches = {}
    for sid in subject_ids:
        sid_match = re.match(r"(\d{5})x(\d+)", sid)
        if not sid_match:
            continue
        prefix, suffix = sid_match.groups()
        for folder in folders:
            if folder.startswith(prefix + ".x") and suffix[:2] in folder.replace("_", "").replace("SCAP1", "").replace("FCAP1", ""):
                matches[sid] = folder
                break
        if len(matches) >= MAX_SUBJECTS_TO_PROCESS:
            break
    return matches

# === STEP 4: Traverse and Extract DICOM Time Fields + Manufacturer Info with Debugging for TotalReadoutTime ===
def extract_time_fields_from_dicoms(base_path):
    time_data = []
    for root, dirs, files in os.walk(base_path):
        dcm_files_read = 0
        for file in files:
            if file.endswith(".dcm"):
                try:
                    dcm_path = os.path.join(root, file)
                    dcm = pydicom.dcmread(dcm_path, stop_before_pixels=True)

                    # Debug: check for any tag containing 'totalreadouttime' ignoring case and spaces
                    for elem in dcm:
                        keyword_norm = elem.keyword.lower().replace(" ", "")
                        if "totalreadouttime" in keyword_norm:
                            print(f"[DEBUG] Found TotalReadoutTime keyword in {dcm_path}: {elem.keyword} = {elem.value}")

                    # Extract time-related fields (case-insensitive 'time' anywhere in keyword)
                    time_fields = {
                        elem.keyword: str(elem.value)
                        for elem in dcm
                        if 'time' in elem.keyword.lower()
                    }

                    # Add Manufacturer info (if present)
                    manufacturer = getattr(dcm, 'Manufacturer', '')
                    model_name = getattr(dcm, 'ManufacturerModelName', '')

                    time_fields['Manufacturer'] = manufacturer
                    time_fields['ManufacturerModelName'] = model_name

                    time_data.append((dcm_path, time_fields))

                    dcm_files_read += 1
                    if dcm_files_read >= MAX_DCM_FILES_PER_FOLDER:
                        break
                except Exception as e:
                    print(f"Failed to read {dcm_path}: {e}")
    return time_data

# === MAIN EXECUTION ===
subject_ids = extract_subject_ids(input_file)
unzipped_folders = list_unzipped_folders(unzipped_dir)
matches = match_subjects_to_folders(subject_ids, unzipped_folders)

print(f"Processing up to {MAX_SUBJECTS_TO_PROCESS} matched subjects...")

all_time_info = []

for sid, folder in matches.items():
    full_folder_path = os.path.join(unzipped_dir, folder)
    print(f"Scanning subject {sid} in folder {folder}")
    time_fields = extract_time_fields_from_dicoms(full_folder_path)
    for path, fields in time_fields:
        all_time_info.append({
            "SubjectID": sid,
            "DICOMPath": path,
            **fields
        })

# === Write Output to CSV ===
if all_time_info:
    fieldnames = set()
    for row in all_time_info:
        fieldnames.update(row.keys())
    fieldnames = sorted(fieldnames)

    with open(output_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_time_info)

    print(f"Extracted time-related DICOM fields (plus manufacturer info) saved to: {output_csv}")
else:
    print("No time-related fields found in any DICOMs.")

