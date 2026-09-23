"""
Ollama adapter for local model inference.
"""

import time
import requests
from driftlab.adapters.base import ModelAdapter, GenerationResult, ModelDescription
from driftlab.config.schemas import GenerationConfig

class OllamaAdapter(ModelAdapter):
    """
    Adapter for interacting with a local Ollama instance.
    """
    
    def __init__(self, model_name: str, base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        
    def generate(self, prompt: str, system_prompt: str, config: GenerationConfig) -> GenerationResult:
        start_time = time.perf_counter()
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "num_predict": config.max_tokens,
                "stop": config.stop_sequences or []
            }
        }
        
        response = requests.post(f"{self.base_url}/api/generate", json=payload)
        response.raise_for_status()
        data = response.json()
        
        end_time = time.perf_counter()
        
        return {
            "text": data.get("response", ""),
            "finish_reason": "stop" if data.get("done") else "length",
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
            "latency_ms": (end_time - start_time) * 1000.0
        }
        
    def describe(self) -> ModelDescription:
        """
        Fetches the model information from the Ollama API.
        """
        response = requests.get(f"{self.base_url}/api/tags")
        response.raise_for_status()
        models = response.json().get("models", [])
        
        model_info = next((m for m in models if m["name"] == self.model_name), None)
        
        if not model_info:
            raise ValueError(f"Model {self.model_name} not found in Ollama instance.")
            
        details = model_info.get("details", {})
        
        return {
            "family": details.get("family", "unknown"),
            "identifier": self.model_name,
            "digest": model_info.get("digest", "unknown")[:12],
            "quantization": details.get("quantization_level", "unknown"),
            "backend_version": "ollama-api"
        }
