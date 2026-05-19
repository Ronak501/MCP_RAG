"""Heuristics for research-gap features.

This module adds two things the current pipeline does not have by itself:

1. Anomaly scoring that combines detections, RAG confidence, and agent output.
2. Simple temporal localization by grouping consecutive suspicious frames.
"""

from __future__ import annotations

from dataclasses import dataclass, field


SUSPICIOUS_OBJECTS = {
    "knife": 0.35,
    "gun": 0.55,
    "baseball bat": 0.30,
    "scissors": 0.20,
    "fire": 0.60,
    "smoke": 0.45,
    "backpack": 0.15,
    "suitcase": 0.15,
}

INCIDENT_PRIORS = {
    "Abuse": 0.18,
    "Arrest": 0.12,
    "Arson": 0.25,
    "Assault": 0.22,
}

SEVERITY_PRIORS = {
    "critical": 0.45,
    "high": 0.32,
    "medium": 0.20,
    "low": 0.10,
}


def _clip_score(value: float) -> float:
    return max(0.0, min(1.0, round(value, 4)))


def compute_anomaly_score(
    detections,
    class_hint=None,
    rag_similarity=0.0,
    agent_decision=None,
):
    """Combine the current evidence into a single anomaly score."""

    score = 0.08
    evidence = []

    for detection in detections or []:
        if detection in SUSPICIOUS_OBJECTS:
            increment = SUSPICIOUS_OBJECTS[detection]
            score += increment
            evidence.append(f"detection:{detection}:{increment:.2f}")

    if class_hint in INCIDENT_PRIORS:
        increment = INCIDENT_PRIORS[class_hint]
        score += increment
        evidence.append(f"class_hint:{class_hint}:{increment:.2f}")

    if rag_similarity:
        increment = rag_similarity * 0.35
        score += increment
        evidence.append(f"rag_similarity:{rag_similarity:.3f}:{increment:.2f}")

    if agent_decision:
        severity = str(agent_decision.get("severity", "low")).lower()
        confidence = float(agent_decision.get("confidence", 0.0))
        severity_bonus = SEVERITY_PRIORS.get(severity, 0.05)
        score += severity_bonus * 0.75
        score += confidence * 0.18
        evidence.append(f"agent_severity:{severity}:{severity_bonus:.2f}")
        evidence.append(f"agent_confidence:{confidence:.2f}:{confidence * 0.18:.2f}")

    if "person" in (detections or []) and score < 0.15:
        score += 0.05

    return _clip_score(score), evidence


@dataclass
class TemporalSegment:
    """A contiguous suspicious frame window."""

    start_frame: int
    end_frame: int
    frame_count: int
    mean_score: float
    peak_score: float
    evidence: list[str] = field(default_factory=list)


class TemporalLocalizer:
    """Track and finalize suspicious frame windows."""

    def __init__(self, threshold=0.55, min_length=2):
        self.threshold = threshold
        self.min_length = min_length
        self._active_start = None
        self._active_scores = []
        self._active_evidence = []
        self._segments = []

    def update(self, frame_index, anomaly_score, evidence=None):
        evidence = evidence or []

        if anomaly_score >= self.threshold:
            if self._active_start is None:
                self._active_start = frame_index
                self._active_scores = []
                self._active_evidence = []

            self._active_scores.append(anomaly_score)
            self._active_evidence.extend(evidence)
            return self.current_segment(frame_index, anomaly_score)

        self._finalize_if_needed(frame_index - 1)
        return None

    def current_segment(self, frame_index, anomaly_score):
        if self._active_start is None:
            return None

        return {
            "start_frame": self._active_start,
            "end_frame": frame_index,
            "length": len(self._active_scores),
            "peak_score": max(self._active_scores + [anomaly_score]),
            "mean_score": sum(self._active_scores) / len(self._active_scores),
        }

    def _finalize_if_needed(self, end_frame):
        if self._active_start is None:
            return

        frame_count = len(self._active_scores)
        if frame_count >= self.min_length:
            self._segments.append(
                TemporalSegment(
                    start_frame=self._active_start,
                    end_frame=end_frame,
                    frame_count=frame_count,
                    mean_score=sum(self._active_scores) / frame_count,
                    peak_score=max(self._active_scores),
                    evidence=sorted(set(self._active_evidence)),
                )
            )

        self._active_start = None
        self._active_scores = []
        self._active_evidence = []

    def finalize(self, last_frame_index=None):
        if self._active_start is not None:
            if last_frame_index is None:
                last_frame_index = self._active_start + max(len(self._active_scores) - 1, 0)
            self._finalize_if_needed(last_frame_index)

        return self._segments
