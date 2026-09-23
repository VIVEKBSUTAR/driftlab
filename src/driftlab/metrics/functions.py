"""
Pure functions to calculate evaluation metrics on LLM outputs.

Includes text matching, sequence similarity, JSON format validity, and
sentence-transformers embedding cosine similarity.
"""

import difflib
import json
import re
from typing import Any, Callable, Dict, List, Optional
import numpy as np

# Cache for sentence-transformers models to prevent reloading weights repeatedly
_EMBEDDING_MODEL_CACHE: Dict[str, Any] = {}


def exact_match(
    prediction: str,
    reference: str,
    case_sensitive: bool = False,
    strip: bool = True,
    **kwargs: Any,
) -> float:
    """Returns 1.0 if prediction exactly matches reference, else 0.0."""
    pred = prediction.strip() if strip else prediction
    ref = reference.strip() if strip else reference
    if not case_sensitive:
        pred = pred.lower()
        ref = ref.lower()
    return 1.0 if pred == ref else 0.0


def contains(
    prediction: str,
    substring: str,
    case_sensitive: bool = False,
    **kwargs: Any,
) -> float:
    """Returns 1.0 if substring is contained within prediction, else 0.0."""
    pred = prediction if case_sensitive else prediction.lower()
    sub = substring if case_sensitive else substring.lower()
    return 1.0 if sub in pred else 0.0


def sequence_similarity(
    prediction: str,
    reference: str,
    **kwargs: Any,
) -> float:
    """Calculates character-level SequenceMatcher ratio between prediction and reference in [0.0, 1.0]."""
    return float(difflib.SequenceMatcher(None, prediction, reference).ratio())


def json_validity(
    prediction: str,
    reference: Optional[str] = None,
    required_keys: Optional[List[str]] = None,
    **kwargs: Any,
) -> float:
    """
    Returns 1.0 if prediction contains valid JSON (and optionally contains all required keys), else 0.0.
    Handles responses enclosed in markdown code fences as well.
    """
    cleaned = prediction.strip()
    # Strip markdown code blocks if present
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
    if match:
        cleaned = match.group(1).strip()

    try:
        parsed = json.loads(cleaned)
        if required_keys:
            if not isinstance(parsed, dict):
                return 0.0
            for key in required_keys:
                if key not in parsed:
                    return 0.0
        return 1.0
    except (json.JSONDecodeError, TypeError, ValueError):
        return 0.0


def embedding_similarity(
    prediction: str,
    reference: str,
    model_name: str = "all-MiniLM-L6-v2",
    **kwargs: Any,
) -> float:
    """
    Calculates cosine similarity between prediction and reference embeddings
    using sentence-transformers. Caches loaded models for inference speed.
    """
    if not prediction.strip() or not reference.strip():
        return 1.0 if prediction.strip() == reference.strip() else 0.0

    if model_name not in _EMBEDDING_MODEL_CACHE:
        from sentence_transformers import SentenceTransformer
        _EMBEDDING_MODEL_CACHE[model_name] = SentenceTransformer(model_name)

    model = _EMBEDDING_MODEL_CACHE[model_name]
    embeddings = model.encode([prediction, reference], convert_to_numpy=True)
    
    vec1 = embeddings[0]
    vec2 = embeddings[1]
    
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0

    sim = float(np.dot(vec1, vec2) / (norm1 * norm2))
    # Clip numerical precision anomalies
    return float(np.clip(sim, -1.0, 1.0))


METRIC_REGISTRY: Dict[str, Callable[..., float]] = {
    "exact_match": exact_match,
    "contains": contains,
    "sequence_similarity": sequence_similarity,
    "json_validity": json_validity,
    "embedding_similarity": embedding_similarity,
}


def compute_metric(
    metric_name: str,
    prediction: str,
    reference: Optional[str] = None,
    **kwargs: Any,
) -> float:
    """Dispatches metric calculation to registered metric function."""
    if metric_name not in METRIC_REGISTRY:
        raise ValueError(
            f"Unknown metric '{metric_name}'. Registered metrics: {list(METRIC_REGISTRY.keys())}"
        )
    fn = METRIC_REGISTRY[metric_name]
    if metric_name == "json_validity":
        return fn(prediction, reference=reference, **kwargs)
    if reference is None:
        raise ValueError(f"Metric '{metric_name}' requires a reference string.")
    return fn(prediction, reference, **kwargs)
