import asyncio
import contextlib
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import update

from compass.adapters.base import AdapterError
from compass.db import Database
from compass.errors import APIError
from compass.models import ImageAsset, Transcription, TranscriptionJob
from compass.routing import require_image_processing
from compass.storage import BlobStore

TERMINAL = {"complete", "failed", "cancelled", "interrupted"}


class JobService:
    def __init__(self, database: Database, registry, blobs: BlobStore, local_only: Callable[[], bool]):
        self.database = database
        self.registry = registry
        self.blobs = blobs
        self.local_only = local_only
        self.tasks: dict[UUID, asyncio.Task] = {}
        self.semaphore = asyncio.Semaphore(1)

    def recover(self) -> None:
        if self.database.engine is None:
            return
        with self.database.sessions() as session:
            session.execute(
                update(TranscriptionJob)
                .where(TranscriptionJob.status.in_(["queued", "running"]))
                .values(
                    status="interrupted",
                    message="The previous process stopped. No automatic retry was started.",
                    updated_at=datetime.now(timezone.utc),
                )
            )
            session.commit()

    def start(self, job_id: UUID) -> None:
        task = asyncio.create_task(self._run(job_id), name=f"transcription-{job_id}")
        self.tasks[job_id] = task
        task.add_done_callback(lambda _task: self.tasks.pop(job_id, None))

    async def shutdown(self) -> None:
        tasks = list(self.tasks.values())
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def cancel(self, job_id: UUID) -> None:
        with self.database.sessions() as session:
            job = session.get(TranscriptionJob, job_id, with_for_update=True)
            if job is None:
                raise APIError(404, "not_found", "This job was not found.")
            if job.status not in TERMINAL:
                job.status = "cancelled"
                job.message = "Cancelled. Already sent data cannot be recalled from a provider."
                job.updated_at = datetime.now(timezone.utc)
                session.commit()
        task = self.tasks.get(job_id)
        if task is not None:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task

    def _fail(self, job_id: UUID, message: str) -> None:
        with self.database.sessions() as session:
            job = session.get(TranscriptionJob, job_id, with_for_update=True)
            if job is not None and job.status not in TERMINAL:
                job.status = "failed"
                job.message = message
                job.updated_at = datetime.now(timezone.utc)
                session.commit()

    async def _run(self, job_id: UUID) -> None:
        working_path: Path | None = None
        temporary = False
        try:
            async with self.semaphore:
                with self.database.sessions() as session:
                    job = session.get(TranscriptionJob, job_id, with_for_update=True)
                    if job is None or job.status in TERMINAL:
                        return
                    image = session.get(ImageAsset, job.image_id)
                    if image is None:
                        raise APIError(404, "not_found", "The source image was not found.")
                    registry = self.registry
                    route = registry.get_route(job.route_id)
                    require_image_processing(image.provenance, route, self.local_only())
                    digest, region = image.sha256, job.region
                    route_id, language, image_id = job.route_id, job.language, image.id
                    job.status = "running"
                    job.message = "Reading the selected image. Output will remain an unreviewed proposal."
                    job.updated_at = datetime.now(timezone.utc)
                    session.commit()

                working_path, temporary = self.blobs.crop(digest, region)
                result = await registry.transcribe(route_id, working_path, language)
                with self.database.sessions() as session:
                    job = session.get(TranscriptionJob, job_id, with_for_update=True)
                    if job is None or job.status in TERMINAL:
                        return
                    transcription = Transcription(
                        image_id=image_id,
                        text=result.text,
                        kind="automatic",
                        engine=result.engine,
                        model_id=result.model_id,
                        language=language,
                        regions=result.regions,
                        warnings=["Automatic transcription; not reviewed.", *result.warnings],
                        input_region=region,
                    )
                    session.add(transcription)
                    session.flush()
                    job.status = "complete"
                    job.message = "Reading complete. Compare the proposal with the original image."
                    job.transcription_id = transcription.id
                    job.updated_at = datetime.now(timezone.utc)
                    session.commit()
        except asyncio.CancelledError:
            # User cancellation already writes cancelled; shutdown leaves interrupted for recovery.
            raise
        except AdapterError as exc:
            self._fail(job_id, exc.message)
        except APIError as exc:
            self._fail(job_id, exc.message)
        except Exception:
            # Do not persist a provider response, key, file path or personal content in error text.
            self._fail(job_id, "Reading failed. Check the route configuration and source image.")
        finally:
            if temporary and working_path is not None:
                working_path.unlink(missing_ok=True)
