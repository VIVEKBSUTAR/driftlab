"""Public response contracts; infrastructure paths are deliberately absent."""

from typing import Any, Literal
from pydantic import BaseModel, Field


class RunSummary(BaseModel):
    id: str
    run_type: Literal["baseline", "candidate"]
    status: Literal["pending", "running", "completed", "failed", "cancelled"]
    model_identifier: str
    created_at: str
    completed_at: str | None = None
    observations_count: int
    expected_observations: int
    dataset_digest: str | None = None
    synthetic: bool
    model_digest: str
    model_provenance: dict[str, Any] | None = None
    generation: dict[str, Any] | None = None
    seed: int | None = None
    metrics: list[str] | None = None
    error: str | None = None


class ObservationResponse(BaseModel):
    task_id: str
    task_key: str
    prompt: str
    reference: str | None
    category: str
    risk_level: str
    repeat_index: int
    raw_output: str
    latency_ms: float
    error: str | None = None
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    scores: dict[str, float]


class AggregateResponse(BaseModel):
    task_id: str
    metric_name: str
    mean_value: float
    std_value: float | None
    repeats_count: int


class RunDetailResponse(RunSummary):
    model: dict[str, str | None]
    observations_total: int
    aggregates: list[AggregateResponse]
    observations: list[ObservationResponse]


class VerdictResponse(BaseModel):
    status: str
    category: str
    metric_id: str
    risk_level: str
    estimate: float
    ci_low: float
    ci_high: float
    p_value: float
    p_adjusted: float
    noise_floor: float
    margin: float
    explanation: str
    details: dict[str, Any] = Field(default_factory=dict)


class ComparisonResponse(BaseModel):
    id: str
    baseline_run_id: str
    candidate_run_id: str
    created_at: str
    verdicts: list[VerdictResponse]
    recommendation: Literal["block", "review", "within_policy"]
    config: dict[str, Any]
    baseline: RunSummary
    candidate: RunSummary
