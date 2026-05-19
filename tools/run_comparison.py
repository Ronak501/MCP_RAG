"""Utility to compare two evaluation runs"""
import csv
from pathlib import Path
import json

def compare_runs(run_a: str, run_b: str):
    pa = Path(run_a)
    pb = Path(run_b)
    if not pa.exists() or not pb.exists():
        print("Run files not found")
        return

    with open(pa) as fa, open(pb) as fb:
        ra = json.load(fa)
        rb = json.load(fb)

    # very simple comparison
    print(f"Run A entries: {len(ra)}")
    print(f"Run B entries: {len(rb)}")


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 3:
        print("Usage: run_comparison.py run_a.json run_b.json")
    else:
        compare_runs(sys.argv[1], sys.argv[2])
