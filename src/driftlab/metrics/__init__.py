"""
Evaluation metrics package for DriftLab.
"""

from driftlab.metrics.functions import (
    exact_match,
    contains,
    sequence_similarity,
    json_validity,
    embedding_similarity,
    compute_metric,
    METRIC_REGISTRY,
)

__all__ = [
    "exact_match",
    "contains",
    "sequence_similarity",
    "json_validity",
    "embedding_similarity",
    "compute_metric",
    "METRIC_REGISTRY",
]
