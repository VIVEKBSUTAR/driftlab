"""
Mock adapter for testing the pipeline without a GPU.
"""

import time
import numpy as np
from typing import Callable, List, Optional, Union
from driftlab.adapters.base import ModelAdapter, GenerationResult, ModelDescription
from driftlab.config.schemas import GenerationConfig


class MockAdapter(ModelAdapter):
    """
    Samples from a caller-specified distribution so the whole pipeline 
    can be tested without a GPU or Ollama running.
    """
    
    def __init__(
        self, 
        response_sampler: Optional[Callable[[str], str]] = None, 
        latency_sampler: Optional[Callable[[], float]] = None,
        seed: int = 42,
        outputs: Optional[List[str]] = None,
    ):
        self.rng = np.random.default_rng(seed)
        self.outputs = outputs
        self._output_idx = 0
        
        if response_sampler is not None:
            self.response_sampler = response_sampler
        elif outputs is not None and len(outputs) > 0:
            def _cycle_sampler(_prompt: str) -> str:
                chosen = self.outputs[self._output_idx % len(self.outputs)]
                self._output_idx += 1
                return chosen
            self.response_sampler = _cycle_sampler
        else:
            self.response_sampler = lambda _prompt: "mock response"

        self.latency_sampler = latency_sampler or (lambda: 5.0)
        
    def generate(self, prompt: str, system_prompt: Optional[str] = None, config: Optional[GenerationConfig] = None) -> GenerationResult:
        start_time = time.time()
        
        # Simulate generation delay
        latency = self.latency_sampler()
        
        # Sample response
        text = self.response_sampler(prompt)
        
        end_time = time.time()
        actual_latency_ms = (end_time - start_time) * 1000.0 + latency
        
        return {
            "text": text,
            "finish_reason": "stop",
            "prompt_tokens": len(prompt.split()),  # Naive token count for mock
            "completion_tokens": len(text.split()), # Naive token count for mock
            "latency_ms": actual_latency_ms,
        }
        
    def describe(self) -> ModelDescription:
        return {
            "family": "mock",
            "identifier": "mock-v1",
            "digest": "00000000",
            "quantization": "none",
            "backend_version": "0.1.0",
        }
