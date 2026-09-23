"""
Provides the ModelAdapter abstract base class and implementations (OllamaAdapter, MockAdapter) for model inference.
"""

from abc import ABC, abstractmethod

class ModelAdapter(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str, config: dict):
        pass

    @abstractmethod
    def describe(self) -> dict:
        pass
