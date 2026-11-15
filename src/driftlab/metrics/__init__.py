"""
Evaluation metrics package for DriftLab.
"""

from driftlab.metrics.functions import (
    answer_match,
    exact_match,
    contains,
    sequence_similarity,
    json_validity,
    embedding_similarity,
    compute_metric,
    METRIC_REGISTRY,
)

__all__ = [
    "answer_match",
    "exact_match",
    "contains",
    "sequence_similarity",
    "json_validity",
    "embedding_similarity",
    "compute_metric",
    "METRIC_REGISTRY",
]
