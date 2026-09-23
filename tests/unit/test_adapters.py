import pytest
from unittest.mock import patch, MagicMock
from driftlab.config.schemas import GenerationConfig
from driftlab.adapters.mock import MockAdapter
from driftlab.adapters.ollama import OllamaAdapter

def test_mock_adapter():
    def mock_sampler(prompt):
        return f"Mock reply to {prompt}"
    
    def mock_latency():
        return 50.0

    adapter = MockAdapter(response_sampler=mock_sampler, latency_sampler=mock_latency)
    config = GenerationConfig()
    
    res = adapter.generate("Hello", "System prompt", config)
    assert "Mock reply to Hello" in res["text"]
    assert res["finish_reason"] == "stop"
    assert res["latency_ms"] >= 50.0
    
    desc = adapter.describe()
    assert desc["family"] == "mock"
    assert desc["identifier"] == "mock-v1"

@patch('driftlab.adapters.ollama.requests.post')
@patch('driftlab.adapters.ollama.requests.get')
def test_ollama_adapter(mock_get, mock_post):
    # Mock describe
    mock_get.return_value.json.return_value = {
        "models": [
            {
                "name": "llama3:latest",
                "digest": "abcdef1234567890",
                "details": {
                    "family": "llama",
                    "quantization_level": "Q4_0"
                }
            }
        ]
    }
    
    # Mock generate
    mock_post.return_value.json.return_value = {
        "response": "Hello world",
        "done": True,
        "prompt_eval_count": 10,
        "eval_count": 5
    }
    
    adapter = OllamaAdapter(model_name="llama3:latest")
    config = GenerationConfig()
    
    # Test describe
    desc = adapter.describe()
    assert desc["family"] == "llama"
    assert desc["identifier"] == "llama3:latest"
    assert desc["quantization"] == "Q4_0"
    assert desc["digest"] == "abcdef123456"
    
    # Test generate
    res = adapter.generate("Hello", "System prompt", config)
    assert res["text"] == "Hello world"
    assert res["finish_reason"] == "stop"
    assert res["prompt_tokens"] == 10
    assert res["completion_tokens"] == 5
    assert res["latency_ms"] >= 0.0
