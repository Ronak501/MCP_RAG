import csv
import json
import time
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


@dataclass
class FrameMetric:
    """Per-frame evaluation metric."""

    run_id: str
    baseline_mode: str
    video_path: str
    class_hint: str
    frame_index: int
    detections: list[str]
    event_text: str
    rag_action: str
    rag_matched_event: str
    rag_similarity: float
    mcp_action: str
    agent_severity: str
    agent_confidence: float
    agent_primary_action: str
    anomaly_score: float
    temporal_segment_start: int | None
    temporal_segment_end: int | None
    temporal_segment_active: bool
    selected_tools: list[str]
    expected_latency_ms: float
    orchestration_notes: str
    expected_action: str
    action_correct: bool
    inference_time_ms: float
    frame_total_time_ms: float
    timestamp: float


def expected_action_for_class(class_hint):
    expected_map = {
        "Assault": "call police",
        "Abuse": "alert supervisor",
        "Arson": "trigger fire emergency",
        "Arrest": "monitor lawful intervention",
    }
    return expected_map.get(class_hint, "monitor situation")


def is_action_correct(expected_action, predicted_action):
    expected = expected_action.lower()
    predicted = predicted_action.lower()

    key_matches = {
        "call police": ["police", "911"],
        "alert supervisor": ["supervisor", "alert"],
        "trigger fire emergency": ["fire", "evacuation", "alarm"],
        "monitor lawful intervention": ["monitor", "lawful", "observe"],
        "monitor situation": ["monitor"],
    }

    if expected not in key_matches:
        return expected in predicted

    return any(token in predicted for token in key_matches[expected])


class EvaluationLogger:
    """Log evaluation metrics in structured per-run files with retention management."""

    def __init__(
        self,
        output_dir="eval_results",
        run_id=None,
        log_format="both",
        max_log_runs=20,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self.log_format = log_format
        self.max_log_runs = max_log_runs
        self.run_id = run_id or self._generate_run_id()

        self.runs_dir = self.output_dir / "runs"
        self.runs_dir.mkdir(exist_ok=True)
        self.summaries_dir = self.output_dir / "summaries"
        self.summaries_dir.mkdir(exist_ok=True)

        self.csv_path = self.runs_dir / f"{self.run_id}.csv"
        self.jsonl_path = self.runs_dir / f"{self.run_id}.jsonl"
        self.summary_path = self.summaries_dir / f"{self.run_id}_summary.json"

        self._count = 0
        self._correct_count = 0
        self._unique_videos = set()
        self._sum_inference_ms = 0.0
        self._sum_total_ms = 0.0
        self._sum_confidence = 0.0
        self._sum_anomaly_score = 0.0
        self._severity_distribution = {}
        self._peak_anomaly_score = 0.0
        self._longest_segment = 0

        self._init_csv_if_needed()
        self._apply_retention_policy()

    @staticmethod
    def _generate_run_id():
        ts = int(time.time())
        return f"run_{ts}_{uuid4().hex[:8]}"

    @staticmethod
    def _frame_to_dict(metric: FrameMetric):
        return {
            "run_id": metric.run_id,
            "baseline_mode": metric.baseline_mode,
            "timestamp": metric.timestamp,
            "video_path": metric.video_path,
            "class_hint": metric.class_hint,
            "frame_index": metric.frame_index,
            "detections": metric.detections,
            "event_text": metric.event_text,
            "rag_action": metric.rag_action,
            "rag_matched_event": metric.rag_matched_event,
            "rag_similarity": metric.rag_similarity,
            "mcp_action": metric.mcp_action,
            "agent_severity": metric.agent_severity,
            "agent_confidence": metric.agent_confidence,
            "agent_primary_action": metric.agent_primary_action,
            "anomaly_score": metric.anomaly_score,
            "temporal_segment_start": metric.temporal_segment_start,
            "temporal_segment_end": metric.temporal_segment_end,
            "temporal_segment_active": metric.temporal_segment_active,
            "selected_tools": metric.selected_tools,
            "expected_latency_ms": metric.expected_latency_ms,
            "orchestration_notes": metric.orchestration_notes,
            "expected_action": metric.expected_action,
            "action_correct": metric.action_correct,
            "inference_time_ms": metric.inference_time_ms,
            "frame_total_time_ms": metric.frame_total_time_ms,
        }

    def _init_csv_if_needed(self):
        if self.log_format in {"csv", "both"} and not self.csv_path.exists():
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "run_id",
                        "baseline_mode",
                        "timestamp",
                        "video_path",
                        "class_hint",
                        "frame_index",
                        "detections",
                        "event_text",
                        "rag_action",
                        "rag_matched_event",
                        "rag_similarity",
                        "mcp_action",
                        "agent_severity",
                        "agent_confidence",
                        "agent_primary_action",
                        "anomaly_score",
                        "temporal_segment_start",
                        "temporal_segment_end",
                        "temporal_segment_active",
                        "selected_tools",
                        "expected_latency_ms",
                        "orchestration_notes",
                        "expected_action",
                        "action_correct",
                        "inference_time_ms",
                        "frame_total_time_ms",
                    ]
                )

    def _apply_retention_policy(self):
        run_files = sorted(self.runs_dir.glob("run_*"), key=lambda p: p.stat().st_mtime)
        excess_count = len(run_files) - self.max_log_runs
        if excess_count <= 0:
            return

        for old_file in run_files[:excess_count]:
            old_file.unlink(missing_ok=True)

            if old_file.stem.endswith("_summary"):
                continue

            summary_file = self.summaries_dir / f"{old_file.stem}_summary.json"
            summary_file.unlink(missing_ok=True)

    def log_frame(self, metric: FrameMetric):
        """Log single frame result in structured per-run files (append mode)."""
        frame_data = self._frame_to_dict(metric)

        if self.log_format in {"jsonl", "both"}:
            with open(self.jsonl_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(frame_data, ensure_ascii=True) + "\n")

        if self.log_format in {"csv", "both"}:
            with open(self.csv_path, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        frame_data["run_id"],
                        frame_data["baseline_mode"],
                        frame_data["timestamp"],
                        frame_data["video_path"],
                        frame_data["class_hint"],
                        frame_data["frame_index"],
                        ", ".join(frame_data["detections"]) if frame_data["detections"] else "none",
                        frame_data["event_text"],
                        frame_data["rag_action"],
                        frame_data["rag_matched_event"],
                        frame_data["rag_similarity"],
                        frame_data["mcp_action"],
                        frame_data["agent_severity"],
                        frame_data["agent_confidence"],
                        frame_data["agent_primary_action"],
                        frame_data["anomaly_score"],
                        frame_data["temporal_segment_start"],
                        frame_data["temporal_segment_end"],
                        frame_data["temporal_segment_active"],
                        ", ".join(frame_data["selected_tools"]) if frame_data["selected_tools"] else "none",
                        frame_data["expected_latency_ms"],
                        frame_data["orchestration_notes"],
                        frame_data["expected_action"],
                        frame_data["action_correct"],
                        frame_data["inference_time_ms"],
                        frame_data["frame_total_time_ms"],
                    ]
                )

        self._count += 1
        self._correct_count += 1 if metric.action_correct else 0
        self._unique_videos.add(metric.video_path)
        self._sum_inference_ms += float(metric.inference_time_ms)
        self._sum_total_ms += float(metric.frame_total_time_ms)
        self._sum_confidence += float(metric.agent_confidence)
        self._sum_anomaly_score += float(metric.anomaly_score)
        self._peak_anomaly_score = max(self._peak_anomaly_score, float(metric.anomaly_score))
        if metric.temporal_segment_active:
            segment_start = metric.temporal_segment_start or 0
            segment_end = metric.temporal_segment_end or segment_start
            self._longest_segment = max(self._longest_segment, segment_end - segment_start + 1)
        self._severity_distribution[metric.agent_severity] = (
            self._severity_distribution.get(metric.agent_severity, 0) + 1
        )

        self.write_summary()

    def get_summary(self):
        """Generate summary statistics for this run."""
        if self._count == 0:
            return None

        summary = {
            "run_id": self.run_id,
            "total_frames": self._count,
            "unique_videos": len(self._unique_videos),
            "decision_accuracy": self._correct_count / self._count,
            "avg_inference_time_ms": self._sum_inference_ms / self._count,
            "avg_frame_total_time_ms": self._sum_total_ms / self._count,
            "avg_confidence": self._sum_confidence / self._count,
            "avg_anomaly_score": self._sum_anomaly_score / self._count,
            "peak_anomaly_score": self._peak_anomaly_score,
            "longest_temporal_segment": self._longest_segment,
            "severity_distribution": self._severity_distribution,
            "csv_path": str(self.csv_path) if self.log_format in {"csv", "both"} else None,
            "jsonl_path": str(self.jsonl_path) if self.log_format in {"jsonl", "both"} else None,
        }

        return summary

    def write_summary(self):
        summary = self.get_summary()
        if not summary:
            return

        with open(self.summary_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)



class BaselineEvaluator:
    """Compare full system vs. simplified baselines."""

    @staticmethod
    def baseline_rag_only(rag_action):
        """Baseline: Just use RAG without agent reasoning."""
        return {
            "severity": "medium",
            "confidence": 0.6,
            "primary_action": rag_action,
            "secondary_actions": [],
            "justification": "RAG-only baseline",
            "additional_notes": "No agent reasoning",
            "anomaly_score": 0.35,
            "inference_time_ms": 1.0,
        }

    @staticmethod
    def baseline_detection_only(detections, class_hint):
        """Baseline: Just use detection + class label."""
        if class_hint == "Assault":
            action = "alert police"
        elif class_hint == "Abuse":
            action = "alert supervisor"
        elif class_hint == "Arson":
            action = "trigger fire alarm"
        elif class_hint == "Arrest":
            action = "monitor situation"
        else:
            action = "continue monitoring"

        return {
            "severity": "high" if any(obj in detections for obj in ["knife", "gun"]) else "medium",
            "confidence": 0.7,
            "primary_action": action,
            "secondary_actions": [],
            "justification": "Detection + class label baseline",
            "additional_notes": "No RAG or agent",
            "anomaly_score": 0.42 if detections else 0.12,
            "inference_time_ms": 0.5,
        }
