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

    def generate(
        self, prompt: str, system_prompt: str, config: GenerationConfig
    ) -> GenerationResult:
        start_time = time.perf_counter()

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
            "options": {
                "temperature": config.temperature,
                "top_p": config.top_p,
                "num_predict": config.max_tokens,
                "stop": config.stop_sequences or [],
                "seed": config.seed,
            },
        }

        response = requests.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=config.timeout_seconds,
            allow_redirects=False,
        )
        if 300 <= response.status_code < 400:
            raise RuntimeError("Inference redirects are not allowed")
        response.raise_for_status()
        if len(response.content) > 4 * 1024 * 1024:
            raise ValueError("Inference response exceeded 4 MiB")
        data = response.json()
        if data.get("error"):
            raise RuntimeError("The inference backend reported a generation error")

        end_time = time.perf_counter()

        return {
            "text": data.get("response", ""),
            "finish_reason": data.get("done_reason") or ("stop" if data.get("done") else "length"),
            "prompt_tokens": data.get("prompt_eval_count", 0),
            "completion_tokens": data.get("eval_count", 0),
            "latency_ms": (end_time - start_time) * 1000.0,
        }

    def describe(self) -> ModelDescription:
        """
        Fetches the model information from the Ollama API.
        """
        response = requests.get(f"{self.base_url}/api/tags", timeout=10, allow_redirects=False)
        if 300 <= response.status_code < 400:
            raise RuntimeError("Inference redirects are not allowed")
        response.raise_for_status()
        models = response.json().get("models", [])

        model_info = next(
            (m for m in models if m.get("name") in (self.model_name, self.model_name + ":latest")),
            None,
        )

        if not model_info:
            raise ValueError(f"Model {self.model_name} not found in Ollama instance.")

        if not model_info.get("digest") or model_info["digest"] == "unknown":
            raise ValueError("Ollama did not provide a model digest")
        self.model_name = model_info["name"]
        details = model_info.get("details", {})
        version_response = requests.get(
            f"{self.base_url}/api/version", timeout=10, allow_redirects=False
        )
        if 300 <= version_response.status_code < 400:
            raise RuntimeError("Inference redirects are not allowed")
        version_response.raise_for_status()
        backend_version = version_response.json().get("version", "unknown")

        return {
            "family": details.get("family", "unknown"),
            "identifier": self.model_name,
            "digest": model_info.get("digest", "unknown"),
            "quantization": details.get("quantization_level", "unknown"),
            "backend_version": backend_version,
        }
