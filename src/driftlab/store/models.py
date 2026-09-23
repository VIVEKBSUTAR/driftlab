"""
SQLAlchemy models for DriftLab SQLite store.

Matches the minimal schema specification:
- Task: task_key, category, risk_level, prompt, expected_output, output_spec.
- Observation: run_id, task_id, repeat_index, seed, raw_output, latency_ms, error.
- StatisticalTest: category, metric_id, method, estimate, ci_low, ci_high, p_value, p_adjusted, noise_floor.
- DriftResult: category, metric_id, risk_level, status, statistical_test_id.
- Experiment, ModelSnapshot, DatasetVersion, Run, MetricResult, PromptAggregate, RiskPolicy.
"""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, Optional
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def generate_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Experiment(Base):
    __tablename__ = "experiments"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    runs = relationship("Run", back_populates="experiment", cascade="all, delete-orphan")


class ModelSnapshot(Base):
    __tablename__ = "model_snapshots"

    id = Column(String, primary_key=True, default=generate_uuid)
    model_family = Column(String, nullable=False)
    identifier = Column(String, nullable=False, index=True)
    digest = Column(String, nullable=False, index=True)
    quantization = Column(String, nullable=True)
    backend_version = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    runs = relationship("Run", back_populates="model_snapshot")


class DatasetVersion(Base):
    __tablename__ = "dataset_versions"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, index=True)
    version = Column(String, nullable=False)
    digest = Column(String, nullable=False, index=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)

    tasks = relationship("Task", back_populates="dataset_version")
    runs = relationship("Run", back_populates="dataset_version")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, default=generate_uuid)
    task_key = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    risk_level = Column(String, nullable=False)  # e.g. low, medium, high, critical
    prompt = Column(Text, nullable=False)
    expected_output = Column(Text, nullable=True)
    output_spec = Column(JSON, nullable=True)
    dataset_version_id = Column(String, ForeignKey("dataset_versions.id"), nullable=True)

    dataset_version = relationship("DatasetVersion", back_populates="tasks")
    observations = relationship("Observation", back_populates="task")
    aggregates = relationship("PromptAggregate", back_populates="task")


class Run(Base):
    __tablename__ = "runs"

    id = Column(String, primary_key=True, default=generate_uuid)
    experiment_id = Column(String, ForeignKey("experiments.id"), nullable=True)
    model_snapshot_id = Column(String, ForeignKey("model_snapshots.id"), nullable=False)
    dataset_version_id = Column(String, ForeignKey("dataset_versions.id"), nullable=True)
    run_type = Column(String, nullable=False, default="baseline")  # baseline or candidate
    status = Column(String, nullable=False, default="pending")  # pending, running, completed, failed
    jsonl_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)

    experiment = relationship("Experiment", back_populates="runs")
    model_snapshot = relationship("ModelSnapshot", back_populates="runs")
    dataset_version = relationship("DatasetVersion", back_populates="runs")
    observations = relationship("Observation", back_populates="run", cascade="all, delete-orphan")
    aggregates = relationship("PromptAggregate", back_populates="run", cascade="all, delete-orphan")


class Observation(Base):
    __tablename__ = "observations"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False, index=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False, index=True)
    repeat_index = Column(Integer, nullable=False)
    seed = Column(Integer, nullable=False)
    raw_output = Column(Text, nullable=False)
    latency_ms = Column(Float, nullable=False)
    error = Column(Text, nullable=True)

    run = relationship("Run", back_populates="observations")
    task = relationship("Task", back_populates="observations")
    metric_results = relationship("MetricResult", back_populates="observation", cascade="all, delete-orphan")


class MetricResult(Base):
    __tablename__ = "metric_results"

    id = Column(String, primary_key=True, default=generate_uuid)
    observation_id = Column(String, ForeignKey("observations.id"), nullable=False, index=True)
    metric_name = Column(String, nullable=False, index=True)
    value = Column(Float, nullable=False)

    observation = relationship("Observation", back_populates="metric_results")


class PromptAggregate(Base):
    __tablename__ = "prompt_aggregates"

    id = Column(String, primary_key=True, default=generate_uuid)
    run_id = Column(String, ForeignKey("runs.id"), nullable=False, index=True)
    task_id = Column(String, ForeignKey("tasks.id"), nullable=False, index=True)
    metric_name = Column(String, nullable=False, index=True)
    mean_value = Column(Float, nullable=False)
    std_value = Column(Float, nullable=True)
    repeats_count = Column(Integer, nullable=False)

    run = relationship("Run", back_populates="aggregates")
    task = relationship("Task", back_populates="aggregates")


class StatisticalTest(Base):
    __tablename__ = "statistical_tests"

    id = Column(String, primary_key=True, default=generate_uuid)
    baseline_run_id = Column(String, ForeignKey("runs.id"), nullable=True)
    candidate_run_id = Column(String, ForeignKey("runs.id"), nullable=True)
    category = Column(String, nullable=False, index=True)
    metric_id = Column(String, nullable=False, index=True)
    method = Column(String, nullable=False)
    estimate = Column(Float, nullable=False)
    ci_low = Column(Float, nullable=False)
    ci_high = Column(Float, nullable=False)
    p_value = Column(Float, nullable=False)
    p_adjusted = Column(Float, nullable=True)
    noise_floor = Column(Float, nullable=True)

    drift_results = relationship("DriftResult", back_populates="statistical_test")


class RiskPolicy(Base):
    __tablename__ = "risk_policies"

    id = Column(String, primary_key=True, default=generate_uuid)
    name = Column(String, nullable=False, unique=True)
    risk_level = Column(String, nullable=False)
    margin = Column(Float, nullable=False)
    alpha = Column(Float, nullable=False, default=0.05)
    min_prompts = Column(Integer, nullable=False, default=10)
    min_repeats = Column(Integer, nullable=False, default=3)
    created_at = Column(DateTime, default=utcnow, nullable=False)


class DriftResult(Base):
    __tablename__ = "drift_results"

    id = Column(String, primary_key=True, default=generate_uuid)
    category = Column(String, nullable=False)
    metric_id = Column(String, nullable=False)
    risk_level = Column(String, nullable=False)
    status = Column(String, nullable=False)  # e.g., 'insufficient_data', 'meaningful_drift', etc.
    statistical_test_id = Column(String, ForeignKey("statistical_tests.id"), nullable=False)

    statistical_test = relationship("StatisticalTest", back_populates="drift_results")
