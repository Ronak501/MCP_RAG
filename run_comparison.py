#!/usr/bin/env python3
"""
Compare full system vs. baselines on the same video.
Run all three modes and log results to eval_results/comparison.csv
"""

import subprocess
import sys
from pathlib import Path

PYTHON_EXE = Path("d:/LANGUAGES/PHYTON/MCP_RAG/.venv/Scripts/python.exe")
PROJECT_ROOT = Path("d:/LANGUAGES/PHYTON/MCP_RAG")

VIDEO_SAMPLE = "data/ucf_crime/Assault/Assault001_x264.mp4"

MODES = [
    {
        "name": "Full System (Agent + RAG)",
        "baseline": None,
        "eval": True,
    },
    {
        "name": "RAG Only (Baseline)",
        "baseline": "rag_only",
        "eval": True,
    },
    {
        "name": "Detection Only (Baseline)",
        "baseline": "detection_only",
        "eval": True,
    },
]


def run_comparison():
    print("🔬 Running comparison of full system vs. baselines...\n")

    for mode in MODES:
        print(f"{'=' * 60}")
        print(f"Mode: {mode['name']}")
        print(f"{'=' * 60}\n")

        cmd = [
            str(PYTHON_EXE),
            "main.py",
            "--video",
            VIDEO_SAMPLE,
            "--stride",
            "120",
            "--conf",
            "0.25",
            "--eval",
        ]

        if mode["baseline"]:
            cmd.extend(["--baseline", mode["baseline"]])

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                capture_output=False,
                text=True,
            )
            if result.returncode != 0:
                print(f"\n⚠️ Mode '{mode['name']}' failed with exit code {result.returncode}\n")
            else:
                print(f"\n✅ Mode '{mode['name']}' completed successfully\n")

        except Exception as e:
            print(f"\n❌ Error running mode '{mode['name']}': {e}\n")

    print(f"\n{'=' * 60}")
    print("✅ Comparison complete!")
    print(f"Results saved to: eval_results/evaluation_log.csv")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    run_comparison()
