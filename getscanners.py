import os
import pydicom
from collections import Counter, defaultdict

def get_scanner_info(dcm_path):
    try:
        ds = pydicom.dcmread(dcm_path, stop_before_pixels=True)
        manufacturer = ds.get('Manufacturer', 'Unknown')
        model = ds.get('ManufacturerModelName', 'Unknown')
        return f"{manufacturer} - {model}"
    except Exception as e:
        return "Unreadable"

def scan_dicom_directory(root_folder):
    scanner_counter = Counter()
    unreadable_files = 0

    for dirpath, _, filenames in os.walk(root_folder):
        for file in filenames:
            if file.lower().endswith(".dcm"):
                full_path = os.path.join(dirpath, file)
                scanner_info = get_scanner_info(full_path)
                if scanner_info == "Unreadable":
                    unreadable_files += 1
                else:
                    scanner_counter[scanner_info] += 1

    return scanner_counter, unreadable_files

# Example usage:
if __name__ == "__main__":
    dicom_root = r"/ceph/chpc/shared/shinjini_kundu_group/working/yash_test/unzippedsubjects"  # Replace with your directory path
    scanner_counts, unreadables = scan_dicom_directory(dicom_root)

    print("\nScanner Models and Counts:")
    for scanner, count in scanner_counts.items():
        print(f"{scanner}: {count}")

    print(f"\nUnreadable files: {unreadables}")
