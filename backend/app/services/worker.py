from datetime import datetime, timedelta, timezone
import os
import socket
import threading
import time
from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import AnalysisRun, JobQueue
from app.services.workflow import execute_analysis_run


WORKER_ID = f"{socket.gethostname()}-pid{os.getpid()}"


def enqueue_analysis_job(db: Session, analysis_run_id: str, max_attempts: int = 3) -> JobQueue:
    job = JobQueue(
        analysis_run_id=analysis_run_id,
        job_type="langgraph_analysis",
        status="queued",
        attempts=0,
        max_attempts=max_attempts,
        payload_json={"analysis_run_id": analysis_run_id},
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def recover_interrupted_jobs(db: Session, stale_seconds: int = 120) -> int:
    """
    Recovers jobs that were in `processing` state when a worker crashed or restarted.
    If `attempts < max_attempts`, resets them to `queued` for bounded retry; otherwise marks `failed`.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=stale_seconds)
    stuck_jobs = list(
        db.execute(
            select(JobQueue).where(
                JobQueue.status == "processing",
                (JobQueue.heartbeat_at.is_(None)) | (JobQueue.heartbeat_at < cutoff),
            )
        ).scalars()
    )
    recovered = 0
    for job in stuck_jobs:
        run = db.execute(select(AnalysisRun).where(AnalysisRun.id == job.analysis_run_id)).scalar_one_or_none()
        if run and run.cancel_requested:
            job.status = "cancelled"
            run.status = "cancelled"
        elif job.attempts < job.max_attempts:
            job.status = "queued"
            job.locked_by = None
            job.last_error = "Recovered after worker interruption; requeued for bounded retry."
            if run:
                run.status = "queued"
                run.retry_count = job.attempts
            recovered += 1
        else:
            job.status = "failed"
            job.last_error = "Exceeded max retry attempts after worker interruption."
            if run:
                run.status = "failed"
                run.error_message = job.last_error
    if stuck_jobs:
        db.commit()
    return recovered


def process_next_queued_job(db: Session) -> Optional[JobQueue]:
    """
    Claims one queued job using PostgreSQL `FOR UPDATE SKIP LOCKED`, executes the
    LangGraph workflow with bounded retries, and updates job & run states.
    """
    job = (
        db.execute(
            select(JobQueue)
            .where(JobQueue.status == "queued")
            .order_by(JobQueue.created_at.asc())
            .with_for_update(skip_locked=True)
        )
        .scalars()
        .first()
    )
    if not job:
        return None

    now = datetime.now(timezone.utc)
    job.status = "processing"
    job.attempts += 1
    job.locked_by = WORKER_ID
    job.locked_at = now
    job.heartbeat_at = now
    db.commit()

    run = db.execute(select(AnalysisRun).where(AnalysisRun.id == job.analysis_run_id)).scalar_one_or_none()
    if not run:
        job.status = "failed"
        job.last_error = "Associated AnalysisRun not found."
        db.commit()
        return job

    run.retry_count = max(0, job.attempts - 1)
    db.commit()

    updated_run = execute_analysis_run(db, run.id)
    db.refresh(job)

    if updated_run.status == "completed":
        job.status = "completed"
        job.heartbeat_at = datetime.now(timezone.utc)
        db.commit()
    elif updated_run.status == "cancelled":
        job.status = "cancelled"
        job.heartbeat_at = datetime.now(timezone.utc)
        db.commit()
    else:
        job.last_error = updated_run.error_message
        # Only retry transient errors if attempts < max_attempts and not a permanent consent/credential failure
        err_msg = (updated_run.error_message or "").lower()
        non_retryable = any(
            k in err_msg
            for k in ("consent", "not configured", "silent fallback", "unsupported ai provider")
        )
        if not non_retryable and job.attempts < job.max_attempts and updated_run.retry_count < updated_run.max_retries:
            job.status = "queued"
            job.locked_by = None
            updated_run.status = "queued"
        else:
            job.status = "failed"
        db.commit()

    return job


class BackgroundWorkerDaemon:
    """In-process or standalone PostgreSQL job queue polling worker."""

    def __init__(self, poll_interval_sec: float = 0.5) -> None:
        self.poll_interval_sec = poll_interval_sec
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        with SessionLocal() as db:
            recover_interrupted_jobs(db, stale_seconds=0)
        self._thread = threading.Thread(target=self._loop, name="techval-pg-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                with SessionLocal() as db:
                    job = process_next_queued_job(db)
                    if job is not None:
                        continue
            except Exception:
                pass
            time.sleep(self.poll_interval_sec)


worker_daemon = BackgroundWorkerDaemon()


if __name__ == "__main__":
    print(f"Starting standalone TechVal AI PostgreSQL Worker ({WORKER_ID})...")
    with SessionLocal() as init_db:
        rec = recover_interrupted_jobs(init_db, stale_seconds=30)
        if rec:
            print(f"Recovered {rec} interrupted job(s).")
    try:
        while True:
            with SessionLocal() as loop_db:
                processed = process_next_queued_job(loop_db)
            if not processed:
                time.sleep(0.5)
    except KeyboardInterrupt:
        print("Worker stopped.")
