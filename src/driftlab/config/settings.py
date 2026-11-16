"""Operator-controlled settings. HTTP requests never select infrastructure."""

import json
import os
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)
    mode: Literal["local", "server"] = "local"
    workspace: Path = Field(default_factory=lambda: Path.cwd())
    api_key: SecretStr | None = None
    ollama_url: str = "http://127.0.0.1:11434"
    allowed_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1", "[::1]"])
    allowed_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    max_body_bytes: int = Field(default=2_097_152, ge=1024, le=16_777_216)
    max_tasks: int = Field(default=500, ge=1, le=5000)
    max_observations: int = Field(default=10000, ge=1, le=100000)
    max_pending_jobs: int = Field(default=16, ge=1, le=1000)
    requests_per_minute: int = Field(default=600, ge=1, le=10000)
    session_seconds: int = Field(default=28800, ge=60, le=86400)
    worker_enabled: bool = True
    cookie_secure: bool = False
    policy_file: Path | None = None
    frontend_dir: Path | None = None

    @model_validator(mode="after")
    def validate_operator_configuration(self):
        self.workspace = self.workspace.expanduser().resolve()
        parsed = urlparse(self.ollama_url)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "ollama_url must be an HTTP(S) origin without embedded credentials or query parameters"
            )
        self.ollama_url = self.ollama_url.rstrip("/")
        if self.api_key and len(self.api_key.get_secret_value()) > 256:
            raise ValueError("API key must not exceed 256 characters")
        if self.mode == "server":
            if not self.api_key or len(self.api_key.get_secret_value()) < 32:
                raise ValueError(
                    "Server mode requires DRIFTLAB_API_KEY with at least 32 characters"
                )
            if not self.cookie_secure:
                raise ValueError(
                    "Server mode requires secure session cookies; terminate TLS at the reverse proxy"
                )
        if not self.allowed_hosts or any(h == "*" for h in self.allowed_hosts):
            raise ValueError(
                "Explicit allowed_hosts are required; wildcard hosts are not supported"
            )
        if any(
            o == "*" or urlparse(o).scheme not in ("http", "https") for o in self.allowed_origins
        ):
            raise ValueError("CORS origins must be explicit HTTP(S) origins")
        return self

    @classmethod
    def from_env(cls):
        values = {}
        for name in cls.model_fields:
            value = os.getenv("DRIFTLAB_" + name.upper())
            if value is not None:
                if name in ("allowed_hosts", "allowed_origins"):
                    value = (
                        json.loads(value)
                        if value.startswith("[")
                        else [p.strip() for p in value.split(",") if p.strip()]
                    )
                values[name] = value
        key_file = os.getenv("DRIFTLAB_API_KEY_FILE")
        if key_file:
            if "api_key" in values:
                raise ValueError("Set only API_KEY or API_KEY_FILE")
            values["api_key"] = Path(key_file).read_text(encoding="utf-8").strip()
        return cls.model_validate(values)
