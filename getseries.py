import json
import os
import sys

def extract_series_description(folder_path):
    if not os.path.isdir(folder_path):
        print(f"Invalid folder path: {folder_path}")
        return

    unique_descriptions = set()

    for filename in os.listdir(folder_path):
        if filename.endswith('.json'):
            file_path = os.path.join(folder_path, filename)
            try:
                with open(file_path, 'r') as file:
                    data = json.load(file)
                    series_description = data.get("SeriesDescription")
                    if series_description:
                        unique_descriptions.add(series_description)
            except json.JSONDecodeError:
                print(f"Error decoding JSON in file: {filename}")
            except Exception as e:
                print(f"Error reading file {filename}: {e}")

    print("\nUnique Series Descriptions:")
    for desc in sorted(unique_descriptions):
        print(f"- {desc}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <folder_path>")
    else:
        extract_series_description(sys.argv[1])

