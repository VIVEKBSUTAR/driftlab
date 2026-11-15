"""Validated generation settings shared by package, CLI, and API."""
from pydantic import BaseModel, ConfigDict, Field


class GenerationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    temperature: float = Field(default=0.7, ge=0, le=2)
    top_p: float = Field(default=1.0, gt=0, le=1)
    max_tokens: int = Field(default=256, ge=1, le=32768)
    stop_sequences: list[str] | None = None
    seed: int | None = None
    timeout_seconds: float = Field(default=60, gt=0, le=3600)
