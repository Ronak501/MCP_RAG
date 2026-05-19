"""Misc utility helpers used by tools"""
from pathlib import Path
import json

def load_json(path: str):
    p = Path(path)
    if not p.exists():
        return None
    with p.open() as f:
        return json.load(f)
