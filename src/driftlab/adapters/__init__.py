"""
Model adapters package for DriftLab.
"""

from driftlab.adapters.base import (
    ModelAdapter,
    GenerationConfig,
    GenerationResult,
)
from driftlab.adapters.mock import MockAdapter
from driftlab.adapters.ollama import OllamaAdapter

__all__ = [
    "ModelAdapter",
    "GenerationConfig",
    "GenerationResult",
    "MockAdapter",
    "OllamaAdapter",
]
