"""
Provides the ModelAdapter abstract base class for model inference.
"""

from abc import ABC, abstractmethod
from typing import TypedDict, Optional
from driftlab.config.schemas import GenerationConfig

class GenerationResult(TypedDict):
    text: str
    finish_reason: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: float

class ModelDescription(TypedDict):
    family: str
    identifier: str
    digest: str
    quantization: str
    backend_version: str

class ModelAdapter(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str, config: GenerationConfig) -> GenerationResult:
        """Generates a response from the model."""
        pass

    @abstractmethod
    def describe(self) -> ModelDescription:
        """Returns metadata describing the model state."""
        pass
