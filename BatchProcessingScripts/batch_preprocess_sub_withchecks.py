#!/usr/bin/env python3

import argparse
import csv
import subprocess
import os
import sys
from pathlib import Path

# Default paths (change if needed)
SCRIPTS_PATH = "/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/code/Preprocessing"
DERIV_ROOT = "/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS/derivatives"

def parse_args():
    parser = argparse.ArgumentParser(description="Batch preprocess with failure checks")
    parser.add_argument("input_file", nargs='?', default=None,
                        help="CSV failure report file or omit for individual subject mode")
    parser.add_argument("--base-path", required=False,
                        default="/ceph/chpc/shared/shinjini_kundu_group/working/yash/tbm_autism-BIDS",
                        help="Base BIDS dataset path")
    parser.add_argument("--subject", help="Subject ID (e.g. sub-XXX)")
    parser.add_argument("--session", help="Session ID (e.g. ses-XXX)")
    parser.add_argument("--run", default="", help="Run ID (e.g. run-YYY)")
    parser.add_argument("--all", action="store_true", help="Run all steps")
    parser.add_argument("--denoise", action="store_true")
    parser.add_argument("--gibbs", action="store_true")
    parser.add_argument("--eddy", action="store_true")
    parser.add_argument("--eddyqc", action="store_true")
    parser.add_argument("--t1qc", action="store_true")
    parser.add_argument("--test", action="store_true",
                        help="If CSV input given, only process first subject")

    args = parser.parse_args()

    # Validation
    if args.input_file:
        if args.subject or args.session:
            parser.error("Specify either a CSV input file or --subject/--session, not both.")
    else:
        if not args.subject or not args.session:
            parser.error("Either provide a CSV file or both --subject and --session.")

    # If --all set, enable all steps
    if args.all:
        args.denoise = True
        args.gibbs = True
        args.eddy = True
        args.eddyqc = True
        args.t1qc = True

    # If no processing flags set and not --all, exit with usage
    if not (args.denoise or args.gibbs or args.eddy or args.eddyqc or args.t1qc):
        parser.error("No processing steps selected. Use --all or individual flags.")

    return args

def read_csv_failures(csv_file):
    failure_map = {}
    with open(csv_file, newline='') as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        for row in reader:
            if len(row) < 10:
                continue
            sub, ses, run = row[0], row[1], row[2]
            denoise_fail = row[6]
            gibbs_fail = row[7]
            eddy_fail = row[8]
            key = f"{sub}_{ses}_{run}"
            failure_map[(key, "denoised")] = denoise_fail
            failure_map[(key, "rmgibbs")] = gibbs_fail
            failure_map[(key, "eddy")] = eddy_fail
    return failure_map

def run_script(script_name, base_path, sub, ses, run=""):
    cmd = [os.path.join(SCRIPTS_PATH, script_name), base_path, sub, ses]
    if run:
        cmd.append(run)
    print("Running:", " ".join(cmd))
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error: {script_name} failed for {sub} {ses} {run} with {e}", file=sys.stderr)

def process_subject_session(sub, ses, run, args, failure_map):
    key = f"{sub}_{ses}_{run}"

    print(f"Processing {sub} {ses} {run}")

    if args.denoise:
        run_script("submit_01_bids_denoise.sh", args.base_path, sub, ses, run)

    if args.gibbs:
        if failure_map.get((key, "denoised"), "False") != "True":
            run_script("submit_02_bids_gibbsringing.sh", args.base_path, sub, ses, run)
        else:
            print(f"Skipping gibbs: denoised step failed for {key}")

    if args.eddy:
        if failure_map.get((key, "rmgibbs"), "False") != "True":
            run_script("submit_03_bids_eddy.sh", args.base_path, sub, ses, run)
        else:
            print(f"Skipping eddy: rmgibbs step failed for {key}")

    if args.eddyqc:
        if failure_map.get((key, "eddy"), "False") != "True":
            run_script("submit_04_bids_eddyqc.sh", args.base_path, sub, ses, run)
        else:
            print(f"Skipping eddyqc: eddy step failed for {key}")

    if args.t1qc:
        t1_qc_path = Path(DERIV_ROOT) / sub / ses / "t1_qc"
        qc_files = list(t1_qc_path.glob("qc*.csv"))
        if qc_files:
            print(f"T1 QC already exists at {t1_qc_path} — skipping.")
        else:
            run_script("submit_05_T1_qc.sh", args.base_path, sub, ses)

    print(f"Finished {sub} {ses} {run}")
    print("-----------------------------")

def main():
    args = parse_args()

    failure_map = {}
    if args.input_file:
        failure_map = read_csv_failures(args.input_file)
        count = 0
        with open(args.input_file, newline='') as f:
            reader = csv.reader(f)
            next(reader)
            for row in reader:
                if len(row) < 3:
                    continue
                sub, ses, run = row[0], row[1], row[2]
                if not sub or not ses:
                    continue
                process_subject_session(sub, ses, run, args, failure_map)
                count += 1
                if args.test:
                    print("Test mode: stopping after first subject.")
                    break
    else:
        # individual mode: no failure checks needed (empty failure_map)
        process_subject_session(args.subject, args.session, args.run, args, failure_map)

if __name__ == "__main__":
    main()
