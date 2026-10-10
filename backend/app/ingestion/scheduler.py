import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.database import engine
from app.db.enums import RecordStatus
from app.db.models.data_source import DataSource
from app.ingestion.sync_engine import SyncEngine

logger = logging.getLogger(__name__)


class IngestionJobQueue:
    """
    Layer 2 Resilient Async Ingestion Worker Queue.
    Manages bounded concurrency, per-connection rate limiting, and exponential retry backoff.
    """

    def __init__(self, max_concurrent_jobs: int = 4):
        self.semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self.active_jobs: Dict[uuid.UUID, dict[str, Any]] = {}
        self._session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async def enqueue_and_execute(
        self,
        source_id: uuid.UUID,
        use_mock_llm: bool = True,
        max_retries: int = 2,
    ) -> dict[str, Any]:
        """Dispatches an ingestion sync job through the worker queue with retry backoff."""
        if source_id in self.active_jobs and self.active_jobs[source_id].get("status") == "running":
            return {
                "source_id": str(source_id),
                "status": "already_running",
                "message": "Sync job already queued or executing in worker pool.",
            }

        self.active_jobs[source_id] = {
            "status": "queued",
            "enqueued_at": datetime.now(timezone.utc).isoformat(),
            "attempt": 0,
        }

        async with self.semaphore:
            self.active_jobs[source_id]["status"] = "running"
            self.active_jobs[source_id]["started_at"] = datetime.now(timezone.utc).isoformat()

            for attempt in range(1, max_retries + 1):
                self.active_jobs[source_id]["attempt"] = attempt
                try:
                    async with self._session_factory() as session:
                        engine_inst = SyncEngine(session)
                        res = await engine_inst.sync_data_source(source_id=source_id, use_mock_llm=use_mock_llm)
                        self.active_jobs[source_id]["status"] = res.status
                        self.active_jobs[source_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
                        self.active_jobs[source_id]["result"] = res.model_dump(mode="json")
                        return self.active_jobs[source_id]
                except Exception as e:
                    logger.warning("Ingestion job attempt %d for %s failed: %s", attempt, source_id, str(e))
                    if attempt < max_retries:
                        await asyncio.sleep(2 ** attempt)
                    else:
                        self.active_jobs[source_id]["status"] = "failed"
                        self.active_jobs[source_id]["error"] = str(e)
                        self.active_jobs[source_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
                        return self.active_jobs[source_id]
        return self.active_jobs[source_id]


# Singleton job queue instance
job_queue = IngestionJobQueue(max_concurrent_jobs=4)


class SyncScheduler:
    """
    Persistent background worker that executes automatic synchronization
    for active connections according to their configured schedule ('off', '1m', '10m').
    Survives application restarts and prevents overlapping runs.
    """

    def __init__(self, check_interval_seconds: int = 15):
        self.check_interval_seconds = check_interval_seconds
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    def start(self):
        """Starts the scheduler loop as an asyncio background task."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run_loop())
            logger.info("Connector SyncScheduler started with IngestionJobQueue.")

    def stop(self):
        """Stops the scheduler loop gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("Connector SyncScheduler stopped.")

    async def _run_loop(self):
        while self._running:
            try:
                await self.tick()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in SyncScheduler tick: {str(e)}", exc_info=False)
            try:
                await asyncio.sleep(self.check_interval_seconds)
            except asyncio.CancelledError:
                break

    async def tick(self):
        """Inspects all active data sources and triggers synchronization if schedule interval elapsed."""
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            stmt = select(DataSource).where(DataSource.status == RecordStatus.ACTIVE)
            res = await session.execute(stmt)
            sources = res.scalars().all()

            for source in sources:
                config = source.connection_config or {}
                schedule_val = str(config.get("schedule", "off")).lower().strip()

                if schedule_val in ("off", "", "none"):
                    continue

                interval_seconds = 60 if schedule_val in ("1m", "1_min", "1min", "1_minute", "every_1_minute") else 600

                # Check if next sync due
                next_sync_raw = config.get("next_sync_at")
                last_synced_at = source.last_synced_at

                is_due = False
                if next_sync_raw:
                    try:
                        next_sync_dt = datetime.fromisoformat(next_sync_raw)
                        if next_sync_dt <= now:
                            is_due = True
                    except Exception:
                        is_due = True
                elif last_synced_at:
                    if last_synced_at + timedelta(seconds=interval_seconds) <= now:
                        is_due = True
                else:
                    # Never synced before and schedule is active
                    is_due = True

                if is_due:
                    # Set next scheduled sync time to prevent immediate re-trigger
                    cfg = dict(config)
                    next_time = now + timedelta(seconds=interval_seconds)
                    cfg["next_sync_at"] = next_time.isoformat()
                    source.connection_config = cfg
                    await session.commit()

                    # Dispatch job through IngestionJobQueue worker pool
                    asyncio.create_task(job_queue.enqueue_and_execute(source.id, use_mock_llm=True))


# Singleton scheduler instance
scheduler = SyncScheduler(check_interval_seconds=15)

