"""
Append-only JSONL persistence and SQLite ingestion for DriftLab runs.

Raw model outputs are written to an append-only JSONL file per run before
anything touches the database. The database is derived; the JSONL file is the source of truth.
"""

import json
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Union
from sqlalchemy.orm import Session
from driftlab.store.models import Observation


def append_observation_record(
    jsonl_path: Union[str, Path],
    record: Dict[str, Any],
) -> None:
    """
    Appends a single observation record to the JSONL file.
    Ensures parent directories exist and flushes writes immediately to guarantee durability.
    """
    path = Path(jsonl_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, mode="a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
        f.flush()


def iter_observation_records(
    jsonl_path: Union[str, Path],
) -> Generator[Dict[str, Any], None, None]:
    """
    Yields parsed JSON observation records from an append-only JSONL file.
    """
    path = Path(jsonl_path)
    if not path.exists():
        return

    with open(path, mode="r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Malformed JSONL on line {line_no} in {path}: {exc}") from exc


def read_observation_records(
    jsonl_path: Union[str, Path],
) -> List[Dict[str, Any]]:
    """
    Reads all records from the JSONL file into a list.
    """
    return list(iter_observation_records(jsonl_path))


def ingest_jsonl_to_database(
    jsonl_path: Union[str, Path],
    session: Session,
    run_id: Optional[str] = None,
) -> int:
    """
    Ingests observation records from the JSONL source of truth into the SQLite database.
    Checks for duplicates based on (run_id, task_id, repeat_index).
    Returns the count of newly inserted observations.
    """
    records = read_observation_records(jsonl_path)
    inserted_count = 0

    for rec in records:
        rec_run_id = rec.get("run_id") or run_id
        if not rec_run_id:
            raise ValueError(f"Record missing run_id: {rec}")

        task_id = rec.get("task_id")
        repeat_index = rec.get("repeat_index", 0)

        # Check if already present to avoid duplication
        existing = (
            session.query(Observation)
            .filter_by(run_id=rec_run_id, task_id=task_id, repeat_index=repeat_index)
            .first()
        )
        if existing:
            continue

        obs = Observation(
            id=rec.get("id"),  # Use existing id if provided, else model default generates UUID
            run_id=rec_run_id,
            task_id=task_id,
            repeat_index=repeat_index,
            seed=rec.get("seed", 0),
            raw_output=rec.get("raw_output", ""),
            latency_ms=rec.get("latency_ms", 0.0),
            error=rec.get("error"),
        )
        session.add(obs)
        inserted_count += 1

    session.flush()
    return inserted_count
