import argparse
import json
from pathlib import Path


def list_runs(base_dir):
    summaries_dir = Path(base_dir) / "summaries"
    if not summaries_dir.exists():
        print("No summaries found.")
        return []

    summary_files = sorted(summaries_dir.glob("*_summary.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not summary_files:
        print("No run summaries found.")
        return []

    print("Available runs (latest first):")
    for file in summary_files:
        with open(file, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(
            f"- {data.get('run_id')} | frames={data.get('total_frames')} | "
            f"accuracy={data.get('decision_accuracy', 0):.2%} | "
            f"avg_total_ms={data.get('avg_frame_total_time_ms', 0):.2f}"
        )

    return summary_files


def show_run(base_dir, run_id):
    summary_path = Path(base_dir) / "summaries" / f"{run_id}_summary.json"
    if not summary_path.exists():
        print(f"Run summary not found: {summary_path}")
        return

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description="Inspect structured evaluation logs")
    parser.add_argument("--base-dir", type=str, default="eval_results", help="Evaluation root directory")
    parser.add_argument("--run-id", type=str, default=None, help="Specific run id to inspect")
    args = parser.parse_args()

    if args.run_id:
        show_run(args.base_dir, args.run_id)
    else:
        list_runs(args.base_dir)


if __name__ == "__main__":
    main()
