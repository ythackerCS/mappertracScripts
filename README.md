# mapperTrac_CHPC

The MAIL lab–specific version of the MapperTrac processing pipeline. This is a modified version of [MaPPeRTrac](https://github.com/LLNL/mappertrac). 

## Current Status

- Batch preprocessing of T1 and diffusion scans using a CSV containing subject, session, and optional run.
- Key preprocessing steps include:
  - Denoising of DWI scans
  - Gibbs ringing correction of DWI scans
  - Eddy current distortion correction of DWI scans
  - Eddy QC of DWI scans
  - T1 QC of T1 scans

## Workflow

This section outlines the full data preparation and processing pipeline, including the scripts and file formats required for automated DICOM to BIDS conversion, session filtering, CSV generation, and batch processing.

### Step-by-Step Script Execution Order

#### **Define Series Mapping**
- **Script**: `BatchProcessingScripts/dcm2bids_mapping.json`  
- This JSON file defines how each DICOM series (based on its description) maps to BIDS-compatible data types.  
  - Example mappings:
    - `"T1w"` → `"anat"`
    - `"Diffusion"` → `"dwi"`
- You must examine all potential series descriptions from your raw DICOMs to define this file correctly.  
⚠️ The mapping must follow the structure provided in the example `dcm2bids_mapping.json`. Using different folder names may break the pipeline. It’s best to modify the provided example directly to match your scan labels.

#### **Batch DICOM to BIDS Conversion**
- **Script**: `BatchProcessingScripts/dcm2bidsautomation_avoidDuplicats.sh`  
- Uses the `dcm2bids_mapping.json` to automatically convert multiple DICOM directories to BIDS format while avoiding duplicate conversions.

#### **Find Compatible Sessions**
- **Script**: `BatchProcessingScripts/find_compatible_sessions.sh`  
- Filters sessions by diffusion scans with a `bval > 30`, which is the minimum threshold required for MapperTrac. This value can be customized.  
- **Output**:  
  - `BatchProcessingScripts/compatible_bval_subjects.txt`  
  - Contains paths to compatible DWI scans.
  - Sessions with multiple qualifying scans are tagged with `-MULTIPLE`.
  - Individual sessions are labeled (e.g., `sub-01x01_ses-01_run-01_dwi.bval`).

#### **Convert Paths to CSV**
- **Script**: `BatchProcessingScripts/convert_paths_to_csv.sh`  
- Converts `compatible_bval_subjects.txt` into a structured CSV file (default: `subjects.csv`) used for batch processing.

#### **Prepare Subject CSV**
- **File**: `BatchProcessingScripts/subjects.csv`  
- **Format**:
  ```csv
  sub,session,run
  sub-01,ses-01,
  sub-02,ses-02,run-01
  sub-03,ses-03,run-01
  ```
- **Note**: `run` is optional. Ensure the structure `sub,session,run` is followed exactly.

## Requirements

- Ensure you have access to the `mappertraccontainer` folder.
- Use a BIDS-compliant directory structure after running `dcm2bids`.

## Batch Preprocessing

#### **Batch Preprocessing**
- **Script**: `BatchProcessingScripts/batch_preprocess_sub.sh`  
- Processes the diffusion and T1 scans for the listed subjects. You can run it on:
  - The entire CSV
  - An individual subject/session/run

##### **Subject Selection Options**
You can provide either:
- A CSV input file (required for batch processing)
- Or specify `--subject`, `--session`, and optionally `--run` directly

##### **Preprocessing Options**
Preprocessing flags:
- `--denoise`, `--gibbs`, `--eddy`, `--eddyqc`, `--t1qc`  
  - `--t1qc` performs QC on T1 scans and can be run independently.
- `--all` runs all steps (⚠️ **not recommended currently**; see warning below).
- All flags are off by default.
- Use `--test` to run only the first subject/session/run listed in your CSV.

## Example Usage

### 1. Using a CSV input file with selected preprocessing steps
```bash
batch_preprocess --input-file /path/to/subject.csv --base-path /path/to/BIDS --denoise --test
```
Runs denoising on all subjects listed in `subject.csv`.

### 2. Single subject and session with selected steps
```bash
batch_preprocess --subject sub-01 --session ses-01 --base-path /path/to/BIDS --gibbs
```
Runs Gibbs ringing correction on `sub-01` and `ses-01` for all DWI scans in the session folder.

### 3. All preprocessing steps (TBD — not recommended)
```bash
batch_preprocess --input-file /path/to/input.csv --base-path /path/to/BIDS --all
```
⚠️ **WARNING**: The `--all` flag attempts to run all steps at once, which will fail due to step dependencies. Use specific flags in sequence instead.

### 4. Test mode for a specific subject/session
```bash
batch_preprocess --input-file /path/to/subject.csv --base-path /path/to/BIDS --eddy --test
```
Runs `eddy` only on the first subject, session, and run listed in `subject.csv`. This is useful to validate preprocessing settings before full execution.

## Additional Folders

### util_scripts
This folder contains potentially useful utility scripts. These may assist with tasks such as data cleaning, reformatting, or metadata preparation. However, these scripts are not fully generalized and will likely require modification to match your dataset or workflow.

### preprocessing
⚠️ **WARNING**: You should **not** modify the contents of this folder if you are using the structure provided in the example `dcm2bids_mapping.json`.

This folder contains the core logic for batch preprocessing. Changing these scripts—especially folder or file names—can break multiple components of the pipeline.

Only make changes if absolutely necessary. **Double-check all edits** to avoid unexpected failures.

## Citation

If you use this pipeline or its derivatives in your work, please cite:

Cai LT, Moon J, Camacho PB, Anderson AT, Chwa WJ, Sutton BP, Markowitz AJ, Palacios EM, Rodriguez A, Manley GT, Shankar S, Bremer PT, Mukherjee P, Madduri RK; TRACK-TBI Investigators.  
**MaPPeRTrac: A Massively Parallel, Portable, and Reproducible Tractography Pipeline.**  
*Neuroinformatics.* 2024 Apr;22(2):177–191. doi: [10.1007/s12021-024-09650-0](https://doi.org/10.1007/s12021-024-09650-0). Epub 2024 Mar 6. PMID: [38446357](https://pubmed.ncbi.nlm.nih.gov/38446357/)
