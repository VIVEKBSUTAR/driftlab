"""Versioned, additive SQLite schema upgrades; never silently discard old data."""

from sqlalchemy import text, inspect
from filelock import FileLock
from driftlab.store.models import Base

SCHEMA_VERSION = 2


def upgrade_schema(engine, workspace):
    with FileLock(str(workspace / ".schema.lock"), timeout=30):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS schema_version (id INTEGER PRIMARY KEY CHECK (id=1), version INTEGER NOT NULL)"
                )
            )
            version = (
                connection.execute(text("SELECT version FROM schema_version WHERE id=1")).scalar()
                or 0
            )
            if version > SCHEMA_VERSION:
                raise RuntimeError(
                    "Workspace schema is newer than this DriftLab installation; upgrade DriftLab"
                )
            Base.metadata.create_all(connection)
            if version < 1:
                for name, table, columns in [
                    ("uq_observation_repeat", "observations", "run_id, task_id, repeat_index"),
                    ("uq_metric_observation", "metric_results", "observation_id, metric_name"),
                    ("uq_prompt_aggregate", "prompt_aggregates", "run_id, task_id, metric_name"),
                    ("uq_model_digest", "model_snapshots", "digest"),
                    ("uq_dataset_digest", "dataset_versions", "digest"),
                ]:
                    connection.execute(
                        text(f"CREATE UNIQUE INDEX IF NOT EXISTS {name} ON {table} ({columns})")
                    )
            if version < 2:
                columns = {
                    column["name"] for column in inspect(connection).get_columns("observations")
                }
                for name, sql_type in [
                    ("finish_reason", "VARCHAR"),
                    ("prompt_tokens", "INTEGER"),
                    ("completion_tokens", "INTEGER"),
                ]:
                    if name not in columns:
                        connection.execute(
                            text(f"ALTER TABLE observations ADD COLUMN {name} {sql_type}")
                        )
            if version < SCHEMA_VERSION:
                connection.execute(
                    text("INSERT OR REPLACE INTO schema_version (id,version) VALUES (1,:version)"),
                    {"version": SCHEMA_VERSION},
                )
