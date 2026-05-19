"""Analyze evaluation logs and produce simple metrics"""
import json
from pathlib import Path

def analyze(run_file: str):
    p = Path(run_file)
    if not p.exists():
        print("Run file not found")
        return

    with p.open() as f:
        data = [json.loads(l) for l in f if l.strip()]

    classes = {}
    for event in data:
        cls = event.get('predicted_class') or event.get('label') or 'unknown'
        classes[cls] = classes.get(cls, 0) + 1

    for k,v in sorted(classes.items(), key=lambda x: -x[1]):
        print(f"{k}: {v}")

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: analyze_logs.py path/to/run.jsonl')
    else:
        analyze(sys.argv[1])
