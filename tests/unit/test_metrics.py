"""
Unit tests for driftlab.metrics.
"""

import pytest
from driftlab.metrics import (
    exact_match,
    contains,
    sequence_similarity,
    json_validity,
    embedding_similarity,
    compute_metric,
)


def test_exact_match():
    assert exact_match("Hello World", "hello world") == 1.0
    assert exact_match("Hello World", "hello world", case_sensitive=True) == 0.0
    assert exact_match("  42  ", "42") == 1.0
    assert exact_match("42", "43") == 0.0


def test_contains():
    assert contains("The capital of France is Paris.", "Paris") == 1.0
    assert contains("The capital of France is Paris.", "london") == 0.0
    assert contains("apple", "APPLE", case_sensitive=True) == 0.0


def test_sequence_similarity():
    sim_identical = sequence_similarity("drift detection", "drift detection")
    assert sim_identical == 1.0

    sim_partial = sequence_similarity("drift detection", "drift validation")
    assert 0.5 < sim_partial < 1.0

    sim_diff = sequence_similarity("abc", "xyz")
    assert sim_diff == 0.0


def test_json_validity():
    valid_json = '{"decision": "drift", "confidence": 0.95}'
    assert json_validity(valid_json) == 1.0
    assert json_validity(valid_json, required_keys=["decision", "confidence"]) == 1.0
    assert json_validity(valid_json, required_keys=["decision", "missing_key"]) == 0.0

    markdown_json = 'Here is the JSON:\n```json\n{"status": "ok"}\n```'
    assert json_validity(markdown_json, required_keys=["status"]) == 1.0

    invalid_json = 'not a json string'
    assert json_validity(invalid_json) == 0.0


def test_embedding_similarity():
    # Exact match strings should have similarity 1.0
    sim_same = embedding_similarity("The quick brown fox", "The quick brown fox")
    assert pytest.approx(sim_same, abs=1e-3) == 1.0

    # Semantically close sentences should have high similarity
    sim_close = embedding_similarity(
        "A small boy is playing with a dog.",
        "A young child plays with a puppy."
    )
    assert sim_close > 0.6

    # Semantically unrelated sentences should have lower similarity
    sim_far = embedding_similarity(
        "A small boy is playing with a dog.",
        "Quantum mechanics describes microscopic particles."
    )
    assert sim_far < sim_close


def test_compute_metric_dispatcher():
    res = compute_metric("exact_match", "foo", "foo")
    assert res == 1.0

    res_json = compute_metric("json_validity", '{"a": 1}')
    assert res_json == 1.0

    with pytest.raises(ValueError, match="Unknown metric"):
        compute_metric("nonexistent_metric", "foo", "bar")
