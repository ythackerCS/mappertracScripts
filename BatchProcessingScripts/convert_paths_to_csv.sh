#!/bin/bash

# Input file (first argument)
input_file="$1"
output_file="${2:-output.csv}"

if [[ ! -f "$input_file" ]]; then
    echo "Error: Input file not found: $input_file"
    exit 1
fi

# Write header
echo "sub,session,run" > "$output_file"

# Read and process each line
while IFS= read -r line; do
    sub=$(echo "$line" | grep -o 'sub-[^/_ \-]*' | head -n 1)
    ses=$(echo "$line" | grep -o 'ses-[^/_ \-]*' | head -n 1)
    run=$(echo "$line" | grep -o 'run-[0-9][0-9]*' | head -n 1)

    if [[ -n "$sub" && -n "$ses" ]]; then
        echo "$sub,$ses,$run" >> "$output_file"
    else
        echo "Warning: Skipping invalid line -> $line"
    fi
done < "$input_file"

echo "CSV written to: $output_file"

