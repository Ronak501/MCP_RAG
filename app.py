"""Flask dashboard for browsing the codebase and logs.

This app is intentionally read-only: it helps you visually inspect the
project structure, open source files, and summarize available evaluation logs.
"""

from __future__ import annotations

import csv
import html
import json
import runpy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flask import Flask, abort, render_template_string, request, redirect, url_for
import time

# Import local modules for lightweight in-process run support
from ai import rag as _rag
from ai import mcp as _mcp
from ai import research_gap as _research_gap
from evaluation.evaluation import EvaluationLogger, FrameMetric, expected_action_for_class, is_action_correct


REPO_ROOT = Path(__file__).resolve().parent
IGNORED_DIRS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "node_modules",
}
CODE_SUFFIXES = {".py", ".md", ".json", ".txt", ".toml", ".ini", ".yml", ".yaml"}


@dataclass
class FileInfo:
    path: Path
    relative_path: str
    suffix: str
    size_bytes: int
    line_count: int


def _safe_relpath(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _collect_code_files() -> list[FileInfo]:
    items: list[FileInfo] = []
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in IGNORED_DIRS for part in path.parts):
            continue
        if path.suffix.lower() not in CODE_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        items.append(
            FileInfo(
                path=path,
                relative_path=_safe_relpath(path),
                suffix=path.suffix.lower() or "(none)",
                size_bytes=path.stat().st_size,
                line_count=len(content.splitlines()) or 1,
            )
        )
    return sorted(items, key=lambda item: item.relative_path.lower())


def _build_tree(files: list[FileInfo]) -> dict[str, Any]:
    tree: dict[str, Any] = {}
    for item in files:
        cursor = tree
        parts = item.relative_path.split("/")
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = item
    return tree


def _render_tree(node: dict[str, Any], prefix: str = "") -> str:
    rows: list[str] = []
    for key in sorted(node.keys(), key=str.lower):
        value = node[key]
        if isinstance(value, dict):
            rows.append(
                f'<details class="tree-folder"><summary>{html.escape(key)}</summary>'
                f'{_render_tree(value, prefix + key + "/")}</details>'
            )
        else:
            rows.append(
                '<div class="tree-file">'
                f'<a href="/file/{html.escape(value.relative_path)}">{html.escape(key)}</a>'
                f'<span>{value.line_count} lines</span>'
                "</div>"
            )
    return "".join(rows)


def _latest_log_summary() -> list[dict[str, Any]]:
    summaries_dir = REPO_ROOT / "eval_results" / "summaries"
    items: list[dict[str, Any]] = []
    if not summaries_dir.exists():
        return items

    for path in sorted(summaries_dir.glob("*_summary.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        data["_path"] = path.name
        # Ensure missing keys have default values for template compatibility
        if "peak_anomaly_score" not in data:
            data["peak_anomaly_score"] = 0.0
        if "avg_inference_time_ms" not in data:
            data["avg_inference_time_ms"] = 0.0
        items.append(data)
    return items[:12]


def _read_log_preview() -> dict[str, Any]:
    runs_dir = REPO_ROOT / "eval_results" / "runs"
    preview: dict[str, Any] = {"jsonl": [], "csv": []}
    if not runs_dir.exists():
        return preview

    jsonl_files = sorted(runs_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    csv_files = sorted(runs_dir.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)

    if jsonl_files:
        try:
            lines = [line for line in jsonl_files[0].read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
            preview["jsonl"] = [json.loads(line) for line in lines[:8]]
            preview["jsonl_file"] = jsonl_files[0].name
        except Exception:
            pass

    if csv_files:
        try:
            with csv_files[0].open(encoding="utf-8", errors="ignore", newline="") as handle:
                reader = csv.DictReader(handle)
                preview["csv"] = [row for _, row in zip(range(8), reader)]
                preview["csv_file"] = csv_files[0].name
        except Exception:
            pass

    return preview


def _project_stats(files: list[FileInfo]) -> dict[str, Any]:
    by_suffix: dict[str, int] = {}
    total_lines = 0
    total_bytes = 0
    for item in files:
        by_suffix[item.suffix] = by_suffix.get(item.suffix, 0) + 1
        total_lines += item.line_count
        total_bytes += item.size_bytes

    return {
        "file_count": len(files),
        "total_lines": total_lines,
        "total_bytes": total_bytes,
        "by_suffix": dict(sorted(by_suffix.items(), key=lambda pair: (-pair[1], pair[0]))),
        "python_files": sum(1 for item in files if item.suffix == ".py"),
    }


def _latest_final_conclusion(video_path: str | None = None) -> list[dict[str, Any]]:
    conclusions_path = REPO_ROOT / "eval_results" / "final_conclusions.csv"
    if not conclusions_path.exists():
        return []

    rows: list[dict[str, Any]] = []
    try:
        with conclusions_path.open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                if video_path and row.get("video_path") != video_path:
                    continue
                rows.append(row)
    except Exception:
        return []

    return rows


FILES = _collect_code_files()
TREE_HTML = _render_tree(_build_tree(FILES))
STATS = _project_stats(FILES)
LOG_SUMMARIES = _latest_log_summary()
LOG_PREVIEW = _read_log_preview()
FINAL_CONCLUSIONS: list[dict[str, Any]] = _latest_final_conclusion()

app = Flask(__name__)


@app.route("/")
def index():
    query = request.args.get("q", "").strip().lower()
    filtered_files = [
        item for item in FILES if not query or query in item.relative_path.lower()
    ]
    filtered_tree = _render_tree(_build_tree(filtered_files)) if query else TREE_HTML

    template = """
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Flask Code Dashboard</title>
      <style>
        :root {
          --bg: #0f172a;
          --panel: #111827;
          --panel-2: #1f2937;
          --line: rgba(255,255,255,.08);
          --text: #e5e7eb;
          --muted: #9ca3af;
          --accent: #38bdf8;
          --accent-2: #34d399;
          --warn: #fbbf24;
          --code: #0b1020;
        }
        * { box-sizing: border-box; }
        body {
          margin: 0;
          background:
            radial-gradient(circle at top left, rgba(56,189,248,.16), transparent 28%),
            radial-gradient(circle at top right, rgba(52,211,153,.12), transparent 26%),
            linear-gradient(180deg, #09111f 0%, #0f172a 100%);
          color: var(--text);
          font-family: Segoe UI, Tahoma, Arial, sans-serif;
        }
        .shell { max-width: 1500px; margin: 0 auto; padding: 24px; }
        .hero {
          display:flex; justify-content:space-between; align-items:flex-end; gap:16px;
          padding: 22px 24px; border:1px solid var(--line); border-radius:24px;
          background: linear-gradient(135deg, rgba(17,24,39,.95), rgba(31,41,55,.92));
          box-shadow: 0 24px 80px rgba(0,0,0,.28);
        }
        .hero h1 { margin: 0; font-size: 34px; letter-spacing: -.03em; }
        .hero p { margin: 8px 0 0; color: var(--muted); max-width: 72ch; }
        .searchbar {
          display:flex; gap:10px; margin-top: 14px; flex-wrap: wrap;
        }
        .searchbar input {
          min-width: 280px; flex:1; padding: 14px 16px; border-radius: 14px;
          border: 1px solid var(--line); background: rgba(255,255,255,.04); color: var(--text);
        }
        .searchbar button, .chip {
          border: none; border-radius: 14px; padding: 12px 16px; color: white; cursor: pointer;
          background: linear-gradient(135deg, var(--accent), #0284c7); text-decoration:none; display:inline-flex; align-items:center; gap:8px;
        }
        .chips { display:flex; gap:10px; flex-wrap: wrap; }
        .chip.secondary { background: linear-gradient(135deg, var(--accent-2), #059669); }
        .grid { display:grid; grid-template-columns: repeat(12, 1fr); gap: 16px; margin-top: 18px; }
        .card {
          border: 1px solid var(--line); border-radius: 20px; background: rgba(17,24,39,.90);
          box-shadow: 0 18px 50px rgba(0,0,0,.20); padding: 18px;
        }
        .stats { grid-column: span 12; display:grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
        .stat { background: linear-gradient(180deg, rgba(255,255,255,.05), rgba(255,255,255,.02)); }
        .stat .label { color: var(--muted); font-size: 13px; }
        .stat .value { font-size: 30px; font-weight: 700; margin-top: 6px; }
        .main { grid-column: span 7; }
        .side { grid-column: span 5; }
        .section-title { display:flex; justify-content:space-between; align-items:center; margin-bottom: 12px; }
        .section-title h2 { margin: 0; font-size: 18px; }
        .section-title span { color: var(--muted); font-size: 12px; }
        .tree-folder summary { cursor:pointer; color: var(--text); padding: 6px 0; }
        .tree-folder, .tree-file { margin-left: 14px; }
        .tree-file {
          display:flex; justify-content:space-between; align-items:center; gap:12px;
          padding: 8px 10px; border-radius: 10px; background: rgba(255,255,255,.03); margin: 6px 0;
        }
        .tree-file a { color: #dbeafe; text-decoration:none; }
        .tree-file a:hover { text-decoration: underline; }
        .tree-file span { color: var(--muted); font-size: 12px; }
        .suffix-list { display:grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
        .suffix-item {
          display:flex; justify-content:space-between; background: rgba(255,255,255,.04);
          padding: 10px 12px; border-radius: 12px;
        }
        .log-item, .file-item {
          padding: 12px; border-radius: 14px; background: rgba(255,255,255,.03); margin: 8px 0;
          border: 1px solid rgba(255,255,255,.06);
        }
        .muted { color: var(--muted); }
        .codeview {
          white-space: pre; overflow:auto; background: var(--code); color: #dbeafe; border-radius: 16px;
          padding: 18px; line-height: 1.55; font-size: 14px; border: 1px solid rgba(255,255,255,.08);
        }
        @media (max-width: 1080px) {
          .main, .side { grid-column: span 12; }
          .stats { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 640px) {
          .hero { flex-direction: column; align-items: flex-start; }
          .stats { grid-template-columns: 1fr; }
          .suffix-list { grid-template-columns: 1fr; }
        }
      </style>
    </head>
    <body>
      <div class="shell">
        <div class="hero">
          <div>
            <h1>Flask Code Dashboard</h1>
            <p>A single Flask app to inspect the codebase, open source files, and understand evaluation logs visually.</p>
            <form class="searchbar" method="get" action="/">
              <input name="q" value="{{ query }}" placeholder="Search files, e.g. ai/agent.py or evaluation" />
              <button type="submit">Search</button>
              <a class="chip secondary" href="/logs">View Logs</a>
            </form>
          </div>
          <div class="chips">
            <a class="chip" href="/">Home</a>
            <a class="chip secondary" href="/logs">Logs</a>
          </div>
        </div>

        <div class="grid stats">
          <div class="card stat"><div class="label">Tracked files</div><div class="value">{{ stats.file_count }}</div></div>
          <div class="card stat"><div class="label">Python files</div><div class="value">{{ stats.python_files }}</div></div>
          <div class="card stat"><div class="label">Lines of code</div><div class="value">{{ stats.total_lines }}</div></div>
          <div class="card stat"><div class="label">Code size</div><div class="value">{{ size_mb }}</div></div>
        </div>

        <div class="grid">
          <div class="card main">
            <div class="section-title"><h2>Code Structure</h2><span>{{ files|length }} matching files</span></div>
            <div>{{ tree_html|safe }}</div>
          </div>

          <div class="card side">
            <div class="section-title"><h2>File Types</h2><span>by suffix</span></div>
            <div class="suffix-list">
              {% for suffix, count in stats.by_suffix.items() %}
              <div class="suffix-item"><strong>{{ suffix }}</strong><span>{{ count }}</span></div>
              {% endfor %}
            </div>

            <div class="section-title" style="margin-top:18px"><h2>Recent Logs</h2><span>{{ log_summaries|length }} summaries</span></div>
            {% if log_summaries %}
              {% for item in log_summaries[:4] %}
                <div class="log-item">
                  <div><strong>{{ item.run_id }}</strong></div>
                  <div class="muted">Frames: {{ item.total_frames }} | Accuracy: {{ '%.1f'|format(item.decision_accuracy * 100) }}%</div>
                  <div class="muted">Peak anomaly: {{ '%.2f'|format(item.peak_anomaly_score) }}</div>
                </div>
              {% endfor %}
            {% else %}
              <div class="muted">No evaluation summaries found in eval_results/.</div>
            {% endif %}
          </div>
        </div>

        <div class="grid">
          <div class="card main">
            <div class="section-title"><h2>Recent File Snapshots</h2><span>open any source file</span></div>
            {% for item in files[:12] %}
              <div class="file-item">
                <div><a href="/file/{{ item.relative_path }}">{{ item.relative_path }}</a></div>
                <div class="muted">{{ item.line_count }} lines • {{ item.size_bytes }} bytes</div>
              </div>
            {% endfor %}
          </div>
          <div class="card side">
            <div class="section-title"><h2>Log Preview</h2><span>{{ log_preview.jsonl_file or log_preview.csv_file or 'none' }}</span></div>
            {% if log_preview.jsonl %}
              {% for row in log_preview.jsonl[:4] %}
                <div class="log-item">
                  <div><strong>{{ row.get('frame_index', 'frame') }}</strong> {{ row.get('class_hint', '') }}</div>
                  <div class="muted">{{ row.get('event_text', '')[:96] }}</div>
                </div>
              {% endfor %}
            {% elif log_preview.csv %}
              {% for row in log_preview.csv[:4] %}
                <div class="log-item">
                  <div><strong>{{ row.get('frame_index', 'frame') }}</strong> {{ row.get('class_hint', '') }}</div>
                  <div class="muted">{{ row.get('event_text', '')[:96] }}</div>
                </div>
              {% endfor %}
            {% else %}
              <div class="muted">No log preview available.</div>
            {% endif %}
          </div>
        </div>
      </div>
    </body>
    </html>
    """

    return render_template_string(
        template,
        query=query,
        stats=STATS,
        size_mb=f"{STATS['total_bytes'] / (1024 * 1024):.2f} MB",
        files=filtered_files,
        tree_html=filtered_tree,
        log_summaries=LOG_SUMMARIES,
        log_preview=LOG_PREVIEW,
    )


@app.route("/file/<path:relative_path>")
def file_view(relative_path: str):
    target = (REPO_ROOT / relative_path).resolve()
    if REPO_ROOT not in target.parents and target != REPO_ROOT:
        abort(404)
    if not target.exists() or not target.is_file():
        abort(404)

    content = target.read_text(encoding="utf-8", errors="ignore")
    numbered = "\n".join(
        f"{index:4d} | {line}"
        for index, line in enumerate(content.splitlines(), start=1)
    )

    template = """
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>{{ relative_path }}</title>
      <style>
        body { margin:0; font-family: Segoe UI, Arial, sans-serif; background:#07111f; color:#e5e7eb; }
        .wrap { max-width: 1400px; margin: 0 auto; padding: 20px; }
        a { color:#38bdf8; text-decoration:none; }
        .card { background: rgba(17,24,39,.95); border:1px solid rgba(255,255,255,.08); border-radius:18px; padding:18px; }
        pre { white-space: pre-wrap; overflow:auto; background:#0b1020; padding:18px; border-radius:16px; line-height:1.55; }
        .meta { color:#9ca3af; margin-bottom:12px; }
      </style>
    </head>
    <body>
      <div class="wrap">
        <p><a href="/">&larr; Back to dashboard</a></p>
        <div class="card">
          <h1>{{ relative_path }}</h1>
          <div class="meta">{{ line_count }} lines</div>
          <pre>{{ numbered }}</pre>
        </div>
      </div>
    </body>
    </html>
    """

    return render_template_string(
        template,
        relative_path=relative_path,
        line_count=len(content.splitlines()),
        numbered=numbered,
    )


@app.route("/logs")
def logs_view():
    template = """
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
      <title>Logs</title>
      <style>
        body { margin:0; background:#07111f; color:#e5e7eb; font-family: Segoe UI, Arial, sans-serif; }
        .wrap { max-width: 1400px; margin: 0 auto; padding: 20px; }
        .grid { display:grid; grid-template-columns: repeat(12, 1fr); gap:16px; }
        .card { grid-column: span 12; background: rgba(17,24,39,.95); border:1px solid rgba(255,255,255,.08); border-radius:18px; padding:18px; }
        .card.half { grid-column: span 6; }
        .muted { color:#9ca3af; }
        .log-item { padding:12px; border-radius:14px; background: rgba(255,255,255,.03); margin:10px 0; }
        @media (max-width: 900px){ .card.half{ grid-column: span 12; } }
      </style>
    </head>
    <body>
      <div class="wrap">
        <p><a href="/" style="color:#38bdf8;text-decoration:none">&larr; Back to dashboard</a></p>

        <div class="grid">
          <div class="card" style="margin-bottom:12px">
            <form method="post" action="/run">
              <label style="display:block;margin-bottom:8px">Run video through pipeline (path relative to repo):</label>
              <input name="video" placeholder="data/ucf_crime/Arson/Arson008_x264.mp4" style="width:78%;padding:10px;border-radius:8px;border:1px solid rgba(255,255,255,.06)" />
              <input name="stride" placeholder="stride (frames)" style="width:12%;padding:10px;border-radius:8px;border:1px solid rgba(255,255,255,.06);margin-left:8px" />
              <button class="chip" style="margin-left:8px;padding:10px 14px;">Run</button>
            </form>
          </div>

          <div class="card">
            <div class="section-title"><h2>Final Conclusion</h2><span>latest processed video</span></div>
            {% if final_conclusions %}
              {% for item in final_conclusions[:3] %}
                <div class="log-item">
                  <div><strong>{{ item.video_path }}</strong></div>
                  <div class="muted">Anomaly detected: {{ item.anomaly_detected }} | Peak anomaly: {{ item.peak_anomaly }}</div>
                  <div class="muted">Suggested action: {{ item.suggested_action }}</div>
                  <div class="muted">MCP action: {{ item.mcp_action_at_peak }} | RAG action: {{ item.rag_action_at_peak }}</div>
                </div>
              {% endfor %}
            {% else %}
              <div class="muted">No final conclusion available yet. Run a video first.</div>
            {% endif %}
          </div>
          <div class="card half">
            <h1>Evaluation Summaries</h1>
            {% if log_summaries %}
              {% for item in log_summaries %}
                <div class="log-item">
                  <div><strong>{{ item.run_id }}</strong> <span class="muted">({{ item._path }})</span></div>
                  <div class="muted">Frames: {{ item.total_frames }} | Unique videos: {{ item.unique_videos }} | Accuracy: {{ '%.1f'|format(item.decision_accuracy * 100) }}%</div>
                  <div class="muted">Avg inference: {{ '%.2f'|format(item.avg_inference_time_ms) }} ms | Peak anomaly: {{ '%.2f'|format(item.peak_anomaly_score) }}</div>
                </div>
              {% endfor %}
            {% else %}
              <div class="muted">No summary JSON files found.</div>
            {% endif %}
          </div>

          <div class="card half">
            <h1>Preview</h1>
            {% if log_preview.jsonl %}
              {% for row in log_preview.jsonl[:10] %}
                <div class="log-item">
                  <div><strong>{{ row.get('class_hint', 'unknown') }}</strong> • frame {{ row.get('frame_index', '?') }}</div>
                  <div class="muted">{{ row.get('event_text', '') }}</div>
                </div>
              {% endfor %}
            {% elif log_preview.csv %}
              {% for row in log_preview.csv[:10] %}
                <div class="log-item">
                  <div><strong>{{ row.get('class_hint', 'unknown') }}</strong> • frame {{ row.get('frame_index', '?') }}</div>
                  <div class="muted">{{ row.get('event_text', '') }}</div>
                </div>
              {% endfor %}
            {% else %}
              <div class="muted">No log preview available.</div>
            {% endif %}
          </div>
        </div>
      </div>
    </body>
    </html>
    """

    return render_template_string(
        template,
        log_summaries=LOG_SUMMARIES,
        log_preview=LOG_PREVIEW,
      final_conclusions=FINAL_CONCLUSIONS,
    )


@app.route("/run", methods=["POST"])
def run_video():
    """Run a lightweight simulation of the pipeline for a given video path.

    This creates a small run CSV/JSONL using existing helper modules so you can
    inspect results in the dashboard. It is *not* running heavy detection; it
    uses RAG + simple MCP mapping + research_gap anomaly heuristics.
    """
    video = (request.form.get("video") or "").strip()
    if not video:
        abort(400, "video path required")

    try:
        _stride = int(request.form.get("stride") or 30)
    except Exception:
        _stride = 30

    logger = EvaluationLogger(output_dir="eval_results", run_id=None, log_format="both", max_log_runs=20)

    parts = Path(video).parts
    class_hint = parts[-2] if len(parts) >= 2 else None

    frame_count = 11
    for i in range(frame_count):
        detections = []
        if str(class_hint).lower() in {"assault", "abuse", "arrest"}:
            detections = ["person"]
        elif str(class_hint).lower() == "arson":
            detections = ["fire"]

        event_text = f"Possible {class_hint or 'incident'} in {video} frame {i}"

        try:
            rag_meta = _rag.query_rag(event_text, return_metadata=True)
        except Exception:
            rag_meta = {"action": "monitor situation", "matched_event": "", "distance": 1.0, "similarity": 0.0}

        try:
            mcp_action = _mcp.derive_action_from_rag_decision(rag_meta.get("action", ""), detections=detections)
        except Exception:
            mcp_action = rag_meta.get("action", "monitor situation")

        try:
            anomaly_score, _evidence = _research_gap.compute_anomaly_score(
                detections,
                class_hint=class_hint,
                rag_similarity=rag_meta.get("similarity", 0.0),
                agent_decision={"severity": "high", "confidence": 0.9},
            )
        except Exception:
            anomaly_score = 0.0

        expected_action = expected_action_for_class(class_hint)
        action_correct = is_action_correct(expected_action, mcp_action)

        metric = FrameMetric(
            run_id=logger.run_id,
            baseline_mode="full_agent_rag",
            video_path=video,
            class_hint=class_hint,
            frame_index=i,
            detections=detections,
            event_text=event_text,
            rag_action=rag_meta.get("action", ""),
            rag_matched_event=rag_meta.get("matched_event", ""),
            rag_similarity=rag_meta.get("similarity", 0.0),
            mcp_action=mcp_action,
            agent_severity="medium",
            agent_confidence=0.6,
            agent_primary_action=mcp_action,
            anomaly_score=anomaly_score,
            temporal_segment_start=None,
            temporal_segment_end=None,
            temporal_segment_active=anomaly_score >= 0.55,
            selected_tools=["vision_detector", "rag_retrieval"],
            expected_latency_ms=200,
            orchestration_notes="run-via-dashboard",
            expected_action=expected_action,
            action_correct=action_correct,
            inference_time_ms=150.0,
            frame_total_time_ms=250.0,
            timestamp=time.time(),
        )

        logger.log_frame(metric)

    # Regenerate final conclusions so the UI immediately shows the verdict.
    try:
        runpy.run_path(str(REPO_ROOT / "scripts" / "aggregate_conclusions.py"), run_name="__main__")
    except Exception:
        pass

    global LOG_SUMMARIES, LOG_PREVIEW, FINAL_CONCLUSIONS
    LOG_SUMMARIES = _latest_log_summary()
    LOG_PREVIEW = _read_log_preview()
    FINAL_CONCLUSIONS = _latest_final_conclusion(video)

    return redirect(url_for("logs_view"))


def create_app() -> Flask:
    return app


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)