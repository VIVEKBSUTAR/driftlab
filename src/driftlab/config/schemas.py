"""
Pydantic schemas for loading and validating policies, experiment configurations, and runtime settings.
"""

from pydantic import BaseModel
from typing import Optional

class BaseConfig(BaseModel):
    pass

class GenerationConfig(BaseModel):
    """Configuration passed to the model adapter for generation."""
    temperature: float = 0.0
    top_p: float = 1.0
    max_tokens: int = 1024
    stop_sequences: Optional[list[str]] = None
