#!/bin/bash

# Input file (first argument)
input_file="$1"
output_file="${2:-output.csv}"

if [[ ! -f "$input_file" ]]; then
    echo "Error: Input file not found: $input_file"
    exit 1
fi

# Write header
echo "sub,session" > "$output_file"

# Read and process each line
while IFS= read -r line; do
    # Extract only the part before the first space
    clean_path=$(echo "$line" | cut -d' ' -f1)

    # Extract subject and session from the cleaned path
    sub=$(echo "$clean_path" | grep -o 'sub-[^/]*')
    ses=$(echo "$clean_path" | grep -o 'ses-[^/]*')

    if [[ -n "$sub" && -n "$ses" ]]; then
        echo "$sub,$ses" >> "$output_file"
    else
        echo "Warning: Skipping invalid line -> $line"
    fi
done < "$input_file"

echo "CSV written to: $output_file"

