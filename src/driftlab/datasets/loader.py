"""Validated JSON/JSONL datasets and bundled, original smoke-test prompts."""
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class TaskSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    task_key: str = Field(min_length=1)
    category: str = Field(default="general", min_length=1)
    risk_level: Literal["low", "medium", "high", "critical"] = "medium"
    prompt: str = Field(min_length=1)
    system_prompt: str | None = None
    expected_output: str | None = None
    output_spec: dict | None = None


def validate_tasks(records: list[dict]) -> list[TaskSpec]:
    if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
        raise ValueError("Tasks must be a list of objects.")
    if not records:
        raise ValueError("Dataset must contain at least one prompt.")
    tasks = [TaskSpec.model_validate({"id": r.get("id", f"t_{i}"),
              "task_key": r.get("task_key", r.get("id", f"t_{i}")), **r})
             for i, r in enumerate(records, 1)]
    if len({t.id for t in tasks}) != len(tasks) or len({t.task_key for t in tasks}) != len(tasks):
        raise ValueError("Task IDs and task keys must be unique within a dataset.")
    return tasks


def load_dataset(path: str | Path) -> list[TaskSpec]:
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"Dataset does not exist: {path}")
    try:
        content = path.read_text(encoding="utf-8")
        records = json.loads(content) if path.suffix.lower() == ".json" else [json.loads(line) for line in content.splitlines() if line.strip()]
        if not isinstance(records, list) or any(not isinstance(r, dict) for r in records):
            raise ValueError("Dataset must be a JSON array or JSONL objects.")
        return validate_tasks(records)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"Invalid dataset: {exc}") from exc


def builtin_tasks() -> list[TaskSpec]:
    """Original functional suite, not a published benchmark or safety certification."""
    records = []
    for i in range(12):
        a, b = i + 7, i * 3 + 2
        records.append(dict(id=f"arithmetic_{i}", task_key=f"arithmetic_{i}", category="arithmetic", risk_level="medium",
            prompt=f"Calculate {a} + {b}. Reply with only the integer.", expected_output=str(a+b)))
    for i in range(20):
        records.append(dict(id=f"structured_{i}", task_key=f"structured_{i}", category="structured_output", risk_level="high",
            prompt=f'Return only a JSON object with exactly these values: "item": {i}, "accepted": true.',
            expected_output=json.dumps({"item": i, "accepted": True}), output_spec={"required_keys": ["item", "accepted"]}))
    return validate_tasks(records)
