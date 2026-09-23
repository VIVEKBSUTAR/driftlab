"""
Unit tests for driftlab.fingerprint.
"""

from driftlab.fingerprint import (
    hash_content,
    hash_object,
    hash_dataset,
    hash_model,
    hash_config,
)


def test_hash_content():
    h1 = hash_content("test data")
    h2 = hash_content("test data")
    h3 = hash_content("different data")
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64


def test_hash_dataset_determinism():
    # Order of tasks in array should not change the computed digest
    tasks_a = [
        {"id": "1", "task_key": "k1", "prompt": "P1", "category": "catA", "risk_level": "low"},
        {"id": "2", "task_key": "k2", "prompt": "P2", "category": "catB", "risk_level": "high"},
    ]
    tasks_b = [
        {"id": "2", "task_key": "k2", "prompt": "P2", "category": "catB", "risk_level": "high"},
        {"id": "1", "task_key": "k1", "prompt": "P1", "category": "catA", "risk_level": "low"},
    ]
    assert hash_dataset(tasks_a) == hash_dataset(tasks_b)

    tasks_modified = [
        {"id": "1", "task_key": "k1", "prompt": "P1 modified", "category": "catA", "risk_level": "low"},
        {"id": "2", "task_key": "k2", "prompt": "P2", "category": "catB", "risk_level": "high"},
    ]
    assert hash_dataset(tasks_a) != hash_dataset(tasks_modified)


def test_hash_model_and_config():
    desc = {
        "family": "llama",
        "identifier": "llama3:8b",
        "quantization": "q4_0",
        "backend_version": "0.1.30",
    }
    h_model = hash_model(desc)
    assert len(h_model) == 64

    conf = {"temperature": 0.0, "top_p": 1.0, "max_tokens": 512}
    h_conf = hash_config(conf)
    assert len(h_conf) == 64
