"""Durable single-host queue with restart recovery and cooperative cancellation."""

from datetime import datetime, timezone
import logging
import threading
from filelock import FileLock, Timeout
from driftlab.store.artifacts import write_error

from driftlab.adapters.ollama import OllamaAdapter
from driftlab.adapters.synthetic import SyntheticAdapter
from driftlab.fingerprint import hash_model
from driftlab.runner.control import RunCancelled, WorkerStopping
from driftlab.store import get_db
from driftlab.store.models import Run, RunJob

logger = logging.getLogger(__name__)


class QueueFull(ValueError):
    pass


class JobQueue:
    def __init__(self, lab, max_pending=16):
        self.lab = lab
        self.max_pending = max_pending
        self.stop_event = threading.Event()
        self.thread = None
        self.lock = FileLock(str(lab.workspace / ".worker.lock"), timeout=0, thread_local=False)

    def enqueue(self, **options):
        with FileLock(str(self.lab.workspace / ".enqueue.lock"), timeout=10):
            with get_db(self.lab.sessions) as session:
                if (
                    session.query(RunJob).filter(RunJob.status.in_(["queued", "running"])).count()
                    >= self.max_pending
                ):
                    raise QueueFull("The evaluation queue is full; wait for a job to complete")
            prepared = self.lab.prepare_run(**options, enqueue=True)
        return prepared[0]

    def recover(self):
        with get_db(self.lab.sessions) as session:
            for job in session.query(RunJob).filter(RunJob.status == "running"):
                run = session.get(Run, job.run_id)
                if run.status == "completed":
                    job.status = "completed"
                elif run.status in ("failed", "cancelled"):
                    job.status = run.status
                else:
                    job.status = "queued"
                    run.status = "pending"

    def start(self):
        self.lock.acquire()
        try:
            self.recover()
            self.stop_event.clear()
            self.thread = threading.Thread(target=self._loop, name="driftlab-worker", daemon=True)
            self.thread.start()
        except BaseException:
            self.lock.release()
            raise

    def stop(self):
        self.stop_event.set()
        if self.thread:
            self.thread.join(timeout=130)
            if self.thread.is_alive():
                logger.warning("Worker did not finish within the shutdown grace period")

    @property
    def healthy(self):
        return bool(self.thread and self.thread.is_alive())

    def _loop(self):
        try:
            while not self.stop_event.is_set():
                ran = self._run_next()
                self.stop_event.wait(0.1 if ran else 0.5)
        except Exception:
            logger.exception("Worker stopped unexpectedly")
        finally:
            self.lock.release()

    def run_once(self):
        """Run a single queued job synchronously, useful for controlled operational checks."""
        if self.healthy:
            raise RuntimeError("Worker is already running")
        with self.lock:
            self.recover()
            return self._run_next()

    def _run_next(self):
        with get_db(self.lab.sessions) as session:
            job = (
                session.query(RunJob)
                .filter_by(status="queued")
                .order_by(RunJob.created_at, RunJob.run_id)
                .first()
            )
            if job is None:
                return False
            run_id, payload = job.run_id, job.payload
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            job.attempts += 1

        def control():
            if self.stop_event.is_set():
                raise WorkerStopping(
                    "Worker stopping; cached generations will resume after restart"
                )
            with get_db(self.lab.sessions) as session:
                if session.get(RunJob, run_id).cancel_requested:
                    raise RunCancelled("Cancelled by the workspace operator")

        try:
            control()
            manifest = payload["manifest"]
            if payload["model"] == "mock":
                refs = {t["prompt"]: t.get("expected_output") or "{}" for t in manifest["tasks"]}
                adapter = SyntheticAdapter(refs, payload["mock_profile"])
            else:
                adapter = OllamaAdapter(payload["model"], base_url=self.lab.ollama_url)
            if hash_model(adapter.describe()) != hash_model(manifest["model"]):
                raise ValueError("Model identity changed after submission; submit a new run")
            self.lab.execute_run((run_id, adapter, manifest), resume=True, check_control=control)
            status, error = "completed", None
        except Timeout:
            status, error = "queued", None
        except WorkerStopping:
            status, error = "queued", None
        except RunCancelled as exc:
            status, error = "cancelled", str(exc)
        except Exception as exc:
            logger.exception("Evaluation job failed", extra={"run_id": run_id})
            status, error = "failed", str(exc)
        with get_db(self.lab.sessions) as session:
            job = session.get(RunJob, run_id)
            job.status, job.error = status, error
            run = session.get(Run, run_id)
            run.status = "pending" if status == "queued" else status
            if status in ("completed", "failed", "cancelled"):
                job.completed_at = datetime.now(timezone.utc)
                run.completed_at = run.completed_at or job.completed_at
            if error:
                write_error(self.lab.artifact_path(run.jsonl_path).with_suffix(".error.txt"), error)
        return True

    def cancel(self, run_id):
        with get_db(self.lab.sessions) as session:
            job = session.get(RunJob, run_id)
            if job is None:
                raise LookupError("Queued run not found")
            if job.status not in ("queued", "running"):
                raise ValueError("Only queued or running jobs can be cancelled")
            job.cancel_requested = 1
            if job.status == "queued":
                job.status = "cancelled"
                job.completed_at = datetime.now(timezone.utc)
                run = session.get(Run, run_id)
                run.status = "cancelled"
                run.completed_at = job.completed_at
