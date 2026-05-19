"""Small helper to tail evaluation logs"""
import time
from pathlib import Path

def tail(file_path: str, lines: int = 20):
    p = Path(file_path)
    if not p.exists():
        print("File does not exist")
        return

    with p.open('r', encoding='utf-8', errors='ignore') as f:
        data = f.read().splitlines()
        for line in data[-lines:]:
            print(line)

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print('Usage: show_logs.py path/to/logfile')
    else:
        tail(sys.argv[1])
