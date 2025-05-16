import os
import pydicom

EXCLUDE_KEYWORDS = {'fmri', 'prage', 't1', 't2', 'rest'}

def get_bval_and_series_description(dcm_path):
    try:
        ds = pydicom.dcmread(dcm_path, stop_before_pixels=True)
        series_desc = ds.get('SeriesDescription', '')
        bval = None
        if (0x0018, 0x9087) in ds:
            bval = float(ds[(0x0018, 0x9087)].value)
        return bval, str(series_desc)
    except Exception:
        return None, None

def find_diffusion_scans(root_folder, output_file="diffusionscansg30.txt"):
    scanned_folders = []

    for dirpath, _, filenames in os.walk(root_folder):
        bvals_found = set()
        skip_due_to_series = False

        for file in filenames:
            if file.lower().endswith(".dcm"):
                full_path = os.path.join(dirpath, file)
                bval, series_desc = get_bval_and_series_description(full_path)

                if series_desc:
                    desc_lower = series_desc.lower()
                    if any(keyword in desc_lower for keyword in EXCLUDE_KEYWORDS):
                        print(f"[SKIP SERIES] {dirpath} -> SeriesDescription: \"{series_desc}\"")
                        skip_due_to_series = True
                        break

                if bval is not None:
                    bvals_found.add(bval)

        if skip_due_to_series:
            continue

        if not bvals_found:
            print(f"[NO BVAL] {dirpath} -> No bval found in any .dcm file")
        else:
            bvals_sorted = sorted(bvals_found)
            print(f"[BVALS] {dirpath} -> Unique bvals: {bvals_sorted}")

        scanned_folders.append(dirpath)

    with open(output_file, "w") as f:
        for folder in scanned_folders:
            f.write(folder + "\n")

    print(f"\nDone. Scanned {len(scanned_folders)} folders (excluding those skipped by SeriesDescription).")
    print(f"Results saved to: {output_file}")

if __name__ == "__main__":
    dicom_root = r"/ceph/chpc/shared/shinjini_kundu_group/working/yash_test/unzippedsubjects"
    find_diffusion_scans(dicom_root)

