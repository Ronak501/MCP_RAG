"""Adaptive MCP Tool Orchestration.

Dynamically selects which analysis tools to invoke based on:
- Scene context (person, crowd, face, object density)
- Latency budget
- Confidence thresholds
- Available resources

This enables efficient, context-aware incident detection without
running all tools on every frame.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal


ToolType = Literal[
    "vision_detector",
    "ocr_analyzer",
    "crowd_analyzer",
    "face_detector",
    "forecasting_model",
    "rag_retrieval",
    "llm_agent",
]


@dataclass
class ToolProfile:
    """Definition of a tool's characteristics."""

    name: ToolType
    latency_ms: float
    confidence_floor: float
    resource_cost: float
    triggers_on: list[str]
    applicable_contexts: list[str]
    skipif_low_detections: bool = False

    def cost_benefit(self, context_score: float) -> float:
        """Heuristic: benefit vs. latency+resource cost."""
        benefit = context_score * (1.0 - self.confidence_floor)
        cost = (self.latency_ms / 100.0) + (self.resource_cost / 10.0)
        return max(0.0, benefit - cost * 0.1)


TOOL_PROFILES: dict[ToolType, ToolProfile] = {
    "vision_detector": ToolProfile(
        name="vision_detector",
        latency_ms=45.0,
        confidence_floor=0.25,
        resource_cost=1.0,
        triggers_on=["person", "object", "anomaly"],
        applicable_contexts=["indoor", "outdoor", "crowd"],
        skipif_low_detections=False,
    ),
    "ocr_analyzer": ToolProfile(
        name="ocr_analyzer",
        latency_ms=120.0,
        confidence_floor=0.70,
        resource_cost=2.5,
        triggers_on=["text_visible"],
        applicable_contexts=["indoor", "urban"],
        skipif_low_detections=True,
    ),
    "crowd_analyzer": ToolProfile(
        name="crowd_analyzer",
        latency_ms=80.0,
        confidence_floor=0.60,
        resource_cost=1.8,
        triggers_on=["person_count_high"],
        applicable_contexts=["crowd", "outdoor", "event"],
        skipif_low_detections=True,
    ),
    "face_detector": ToolProfile(
        name="face_detector",
        latency_ms=60.0,
        confidence_floor=0.75,
        resource_cost=1.2,
        triggers_on=["face_present"],
        applicable_contexts=["indoor", "close_range"],
        skipif_low_detections=True,
    ),
    "forecasting_model": ToolProfile(
        name="forecasting_model",
        latency_ms=30.0,
        confidence_floor=0.50,
        resource_cost=0.8,
        triggers_on=["temporal_pattern", "anomaly_trend"],
        applicable_contexts=["all"],
        skipif_low_detections=False,
    ),
    "rag_retrieval": ToolProfile(
        name="rag_retrieval",
        latency_ms=15.0,
        confidence_floor=0.40,
        resource_cost=0.5,
        triggers_on=["decision_needed"],
        applicable_contexts=["all"],
        skipif_low_detections=False,
    ),
    "llm_agent": ToolProfile(
        name="llm_agent",
        latency_ms=800.0,
        confidence_floor=0.45,
        resource_cost=3.0,
        triggers_on=["reasoning_needed", "severity_high"],
        applicable_contexts=["all"],
        skipif_low_detections=False,
    ),
}


@dataclass
class SceneContext:
    """Inferred properties of the current frame."""

    has_person: bool
    person_count: int
    has_face: bool
    has_text: bool
    has_crowd: bool
    object_density: float
    indoor_likely: bool
    outdoor_likely: bool
    anomaly_prior: float
    avg_latency_budget_ms: float = 300.0


@dataclass
class OrchestrationDecision:
    """Which tools to invoke and why."""

    selected_tools: list[ToolType] = field(default_factory=list)
    skipped_tools: list[ToolType] = field(default_factory=list)
    reasoning: dict[ToolType, str] = field(default_factory=dict)
    total_expected_latency_ms: float = 0.0
    total_resource_cost: float = 0.0


def infer_scene_context(
    detections: list[str],
    class_hint: str | None = None,
    prior_anomaly_score: float = 0.1,
    avg_frame_latency_ms: float = 100.0,
) -> SceneContext:
    """Infer scene characteristics from detections and history."""

    detections_lower = [d.lower() for d in detections]
    has_person = "person" in detections_lower
    person_count = min(sum(1 for d in detections_lower if "person" in d), 10)
    has_face = "face" in detections_lower or "head" in detections_lower
    has_text = any(t in detections_lower for t in ["sign", "text", "label"])
    has_crowd = person_count > 3

    object_density = len(detections) / 15.0

    indoor_likely = any(x in detections_lower for x in ["chair", "table", "desk", "ceiling"])
    outdoor_likely = any(x in detections_lower for x in ["tree", "sky", "ground"])

    anomaly_prior = prior_anomaly_score
    if class_hint in ["Abuse", "Assault", "Arson"]:
        anomaly_prior = max(anomaly_prior, 0.35)
    elif class_hint == "Arrest":
        anomaly_prior = max(anomaly_prior, 0.25)

    return SceneContext(
        has_person=has_person,
        person_count=person_count,
        has_face=has_face,
        has_text=has_text,
        has_crowd=has_crowd,
        object_density=object_density,
        indoor_likely=indoor_likely,
        outdoor_likely=outdoor_likely,
        anomaly_prior=anomaly_prior,
        avg_latency_budget_ms=300.0 - (avg_frame_latency_ms * 0.5),
    )


def _get_context_score(context: SceneContext, tool: ToolProfile) -> float:
    """Score how relevant a tool is for the scene."""

    context_match = 0.0
    if "all" in tool.applicable_contexts:
        context_match = 0.8
    else:
        indoor_ctx = "indoor" if context.indoor_likely else ""
        outdoor_ctx = "outdoor" if context.outdoor_likely else ""
        crowd_ctx = "crowd" if context.has_crowd else ""

        if indoor_ctx and indoor_ctx in tool.applicable_contexts:
            context_match += 0.5
        if outdoor_ctx and outdoor_ctx in tool.applicable_contexts:
            context_match += 0.5
        if crowd_ctx and crowd_ctx in tool.applicable_contexts:
            context_match += 0.4

    trigger_match = 0.0
    for trigger in tool.triggers_on:
        if trigger == "person" and context.has_person:
            trigger_match += 0.3
        elif trigger == "person_count_high" and context.has_crowd:
            trigger_match += 0.4
        elif trigger == "face_present" and context.has_face:
            trigger_match += 0.35
        elif trigger == "text_visible" and context.has_text:
            trigger_match += 0.2
        elif trigger == "object":
            trigger_match += context.object_density * 0.3
        elif trigger == "anomaly" and context.anomaly_prior > 0.2:
            trigger_match += context.anomaly_prior * 0.4
        elif trigger == "decision_needed":
            trigger_match += 0.2
        elif trigger == "reasoning_needed" and context.anomaly_prior > 0.3:
            trigger_match += 0.3
        elif trigger == "severity_high" and context.anomaly_prior > 0.4:
            trigger_match += 0.5
        elif trigger == "temporal_pattern":
            trigger_match += 0.15
        elif trigger == "anomaly_trend":
            trigger_match += 0.1

    return min(1.0, context_match + trigger_match)


def orchestrate(
    context: SceneContext,
    force_tools: list[ToolType] | None = None,
) -> OrchestrationDecision:
    """Decide which tools to invoke given the scene context."""

    decision = OrchestrationDecision()

    for tool_type, tool_profile in TOOL_PROFILES.items():
        if force_tools and tool_type not in force_tools:
            continue

        if tool_profile.skipif_low_detections and context.object_density < 0.1:
            decision.skipped_tools.append(tool_type)
            decision.reasoning[tool_type] = "Low object density, skipping expensive tool"
            continue

        context_score = _get_context_score(context, tool_profile)

        if context_score < 0.15 and tool_type not in ["rag_retrieval"]:
            decision.skipped_tools.append(tool_type)
            decision.reasoning[tool_type] = f"Low context relevance ({context_score:.2f})"
            continue

        latency_ok = (
            decision.total_expected_latency_ms + tool_profile.latency_ms
            <= context.avg_latency_budget_ms
        )
        if not latency_ok and tool_type not in ["vision_detector", "rag_retrieval"]:
            decision.skipped_tools.append(tool_type)
            decision.reasoning[tool_type] = (
                f"Latency budget exceeded ({decision.total_expected_latency_ms + tool_profile.latency_ms:.0f}ms "
                f"> {context.avg_latency_budget_ms:.0f}ms)"
            )
            continue

        decision.selected_tools.append(tool_type)
        decision.total_expected_latency_ms += tool_profile.latency_ms
        decision.total_resource_cost += tool_profile.resource_cost
        benefit = tool_profile.cost_benefit(context_score)
        decision.reasoning[tool_type] = (
            f"Selected (context_score={context_score:.2f}, benefit={benefit:.2f})"
        )

    if "rag_retrieval" not in decision.selected_tools:
        decision.selected_tools.append("rag_retrieval")
        decision.total_expected_latency_ms += TOOL_PROFILES["rag_retrieval"].latency_ms
        decision.total_resource_cost += TOOL_PROFILES["rag_retrieval"].resource_cost
        decision.reasoning["rag_retrieval"] = "Always included for baseline decision"

    return decision


@dataclass
class OrchestrationMetric:
    """Track orchestration efficiency across frames."""

    frame_index: int
    selected_tool_count: int
    skipped_tool_count: int
    expected_latency_ms: float
    actual_latency_ms: float
    tool_selection: list[ToolType] = field(default_factory=list)
    timestamp: float = 0.0

    def efficiency_ratio(self) -> float:
        """How well we used available latency budget."""
        if self.expected_latency_ms == 0:
            return 1.0
        return min(1.0, 300.0 / self.expected_latency_ms)


class OrchestrationLogger:
    """Track tool selection patterns across runs."""

    def __init__(self):
        self._metrics: list[OrchestrationMetric] = []
        self._tool_selection_counts: dict[ToolType, int] = {t: 0 for t in TOOL_PROFILES}
        self._tool_skip_counts: dict[ToolType, int] = {t: 0 for t in TOOL_PROFILES}
        self._total_frames = 0

    def log_orchestration(self, metric: OrchestrationMetric):
        """Record a single frame's orchestration decision."""
        self._metrics.append(metric)
        self._total_frames += 1

        for tool in metric.tool_selection:
            self._tool_selection_counts[tool] += 1

    def get_summary(self) -> dict:
        """Aggregate statistics."""
        if not self._metrics:
            return {}

        avg_expected_latency = sum(m.expected_latency_ms for m in self._metrics) / len(
            self._metrics
        )
        avg_actual_latency = sum(m.actual_latency_ms for m in self._metrics) / len(
            self._metrics
        )
        avg_efficiency = sum(m.efficiency_ratio() for m in self._metrics) / len(self._metrics)

        tool_frequencies = {
            tool: (count / self._total_frames if self._total_frames > 0 else 0)
            for tool, count in self._tool_selection_counts.items()
        }

        return {
            "total_frames": self._total_frames,
            "avg_expected_latency_ms": avg_expected_latency,
            "avg_actual_latency_ms": avg_actual_latency,
            "avg_efficiency_ratio": avg_efficiency,
            "tool_frequencies": tool_frequencies,
            "tool_selection_counts": self._tool_selection_counts,
        }
