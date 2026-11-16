"""Explicit reference-based synthetic adapter, reproducible per generation seed."""

import numpy as np
from driftlab.adapters.mock import MockAdapter


class SyntheticAdapter(MockAdapter):
    def __init__(self, references, profile="stable"):
        super().__init__()
        self.references = references
        self.profile = profile

    def generate(self, prompt, system_prompt=None, config=None):
        rng = np.random.default_rng(config.seed)
        success = rng.random() < (0.95 if self.profile == "stable" else 0.45)
        return {
            "text": self.references[prompt] if success else "synthetic incorrect output",
            "latency_ms": 0.0,
            "finish_reason": "stop",
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }

    def describe(self):
        return {
            **super().describe(),
            "identifier": f"mock-{self.profile}",
            "profile": self.profile,
            "backend_version": "seeded-reference-v2",
        }
