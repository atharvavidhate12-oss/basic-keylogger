#!/usr/bin/env python3
"""
fim.py — Simple File Integrity Monitor (SHA-256)

Usage:
    # create baseline for a directory
    python fim.py --init /path/to/dir --baseline baseline.json

    # check against baseline
    python fim.py --check /path/to/dir --baseline baseline.json

    # compute hash for a single file
    python fim.py --hash /path/to/file
"""

import os
import argparse
import json
import hashlib
from datetime import datetime

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def walk_and_hash(root):
    results = {}
    for dirpath, dirnames, filenames in os.walk(root):
        for fname in filenames:
            full = os.path.join(dirpath, fname)
            try:
                h = sha256_file(full)
                results[full] = {"sha256": h, "mtime": os.path.getmtime(full), "size": os.path.getsize(full)}
            except Exception as e:
                results[full] = {"error": str(e)}
    return results

def save_baseline(baseline, filename):
    data = {"created_at": datetime.utcnow().isoformat() + "Z", "files": baseline}
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Baseline saved to {filename}")

def load_baseline(filename):
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def compare(baseline_data, current):
    baseline_files = baseline_data.get("files", {})
    added = []
    removed = []
    modified = []

    for path in current:
        if path not in baseline_files:
            added.append(path)
        else:
            b = baseline_files[path]
            if current[path].get("sha256") != b.get("sha256"):
                modified.append(path)

    for path in baseline_files:
        if path not in current:
            removed.append(path)

    return {"added": added, "removed": removed, "modified": modified}

def main():
    p = argparse.ArgumentParser(description="Simple File Integrity Monitor (SHA-256)")
    p.add_argument("--init", help="Initialize baseline for directory")
    p.add_argument("--baseline", help="Baseline file (JSON)", required=False)
    p.add_argument("--check", help="Check directory against baseline")
    p.add_argument("--hash", help="Compute hash for a single file")
    args = p.parse_args()

    if args.hash:
        if not os.path.isfile(args.hash):
            print("File not found.")
            return
        print(f"{args.hash}: {sha256_file(args.hash)}")
        return

    if args.init:
        baseline = walk_and_hash(args.init)
        baseline_file = args.baseline or "baseline.json"
        save_baseline(baseline, baseline_file)
        return

    if args.check and args.baseline:
        if not os.path.exists(args.baseline):
            print("Baseline file not found.")
            return
        baseline_data = load_baseline(args.baseline)
        current = walk_and_hash(args.check)
        comp = compare(baseline_data, current)
        print("=== File Integrity Check Report ===")
        print(f"Added files: {len(comp['added'])}")
        for pth in comp['added'][:20]:
            print(" +", pth)
        print(f"Removed files: {len(comp['removed'])}")
        for pth in comp['removed'][:20]:
            print(" -", pth)
        print(f"Modified files: {len(comp['modified'])}")
        for pth in comp['modified'][:20]:
            print(" *", pth)
        # optionally write a small report
        report = {
            "checked_at": datetime.utcnow().isoformat() + "Z",
            "summary": comp
        }
        with open("fim_report.json", "w", encoding="utf-8") as rf:
            json.dump(report, rf, indent=2)
        print("Report saved to fim_report.json")
        return

    p.print_help()

if __name__ == "__main__":
    main()
