import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.database import engine
from app.db.enums import RecordStatus
from app.db.models.data_source import DataSource
from app.ingestion.sync_engine import SyncEngine

logger = logging.getLogger(__name__)


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
            logger.info("Connector SyncScheduler started.")

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

                    # Trigger synchronization via worker task using a separate session
                    asyncio.create_task(self._execute_scheduled_sync(source.id))

    async def _execute_scheduled_sync(self, source_id):
        """Executes sync for a single data source in its own isolated database session."""
        try:
            async with self._session_factory() as sync_session:
                engine_inst = SyncEngine(sync_session)
                result = await engine_inst.sync_data_source(source_id=source_id, use_mock_llm=True)
                logger.info(
                    f"Scheduled sync completed for source {source_id} ({result.source_name}): "
                    f"{result.documents_synced} docs, status={result.status}"
                )
        except Exception as e:
            logger.error(f"Scheduled sync failed for source {source_id}: {str(e)}", exc_info=False)


# Singleton scheduler instance
scheduler = SyncScheduler(check_interval_seconds=15)
