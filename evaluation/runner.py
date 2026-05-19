"""Simple evaluation runner utilities"""
from pathlib import Path
import json

def evaluate_run(jsonl_path: str):
    p = Path(jsonl_path)
    if not p.exists():
        raise FileNotFoundError(jsonl_path)

    metrics = {"total": 0, "by_class": {}}
    with p.open() as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            metrics["total"] += 1
            cls = entry.get("predicted_class") or entry.get("label") or "unknown"
            metrics["by_class"][cls] = metrics["by_class"].get(cls, 0) + 1

    return metrics
