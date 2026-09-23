"""
Deterministic cryptographic fingerprinting for dataset versions, model snapshots, and configurations.
"""

import hashlib
import json
from typing import Any, Dict, List, Union


def hash_content(data: Union[str, bytes]) -> str:
    """Computes a SHA-256 hex digest of string or bytes."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def hash_object(obj: Any) -> str:
    """Computes a deterministic SHA-256 hex digest of a JSON-serializable object."""
    canonical_json = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hash_content(canonical_json)


def hash_dataset(tasks: List[Dict[str, Any]]) -> str:
    """
    Computes a deterministic digest for a collection of tasks.
    Sorts tasks by task_key or id for canonical order.
    """
    normalized = []
    for t in sorted(tasks, key=lambda x: str(x.get("task_key") or x.get("id") or "")):
        normalized.append({
            "task_key": t.get("task_key"),
            "category": t.get("category"),
            "risk_level": t.get("risk_level"),
            "prompt": t.get("prompt"),
            "expected_output": t.get("expected_output"),
            "output_spec": t.get("output_spec"),
        })
    return hash_object(normalized)


def hash_model(model_desc: Dict[str, Any]) -> str:
    """Computes a deterministic digest for model description metadata."""
    normalized = {
        "family": model_desc.get("family", ""),
        "identifier": model_desc.get("identifier", ""),
        "quantization": model_desc.get("quantization", ""),
        "backend_version": model_desc.get("backend_version", ""),
    }
    return hash_object(normalized)


def hash_config(config_dict: Dict[str, Any]) -> str:
    """Computes a deterministic digest for generation or experiment configuration."""
    return hash_object(config_dict)
