"""Evaluation utilities package

Exports core evaluation classes and helpers from the moved module.
"""

from .evaluation import (
	FrameMetric,
	expected_action_for_class,
	is_action_correct,
	EvaluationLogger,
	BaselineEvaluator,
)

__all__ = [
	"FrameMetric",
	"expected_action_for_class",
	"is_action_correct",
	"EvaluationLogger",
	"BaselineEvaluator",
	"evaluate_run",
]

from .runner import evaluate_run
"""Evaluation package: structured logging and analysis."""

__all__ = ["evaluation"]
