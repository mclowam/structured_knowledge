import asyncio
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Config, settings
from app.db.session import async_session_maker
from app.models.library import Library, LibraryStatus
from app.repositories.library import LibraryRepository
from app.use_cases.compression import build_compression_service
from app.use_cases.extraction import build_extraction_service

logger = logging.getLogger(__name__)


async def _library_ids_by_status(
    session_factory: async_sessionmaker[AsyncSession],
    status: LibraryStatus,
) -> list[uuid.UUID]:
    async with session_factory() as session:
        libraries = await LibraryRepository(session).list_by_status(status)
        return [library.id for library in libraries]


async def _process_library(
    session_factory: async_sessionmaker[AsyncSession],
    library_id: uuid.UUID,
    expected_status: LibraryStatus,
    settings: Config,
) -> None:
    try:
        async with session_factory() as session:
            library_repo = LibraryRepository(session)
            library = await library_repo.get_by_id(library_id)
            if library is None or library.status != expected_status:
                return

            status_before = library.status.value
            logger.info(
                "Processing library_id=%s status_before=%s",
                library.id,
                status_before,
            )

            if expected_status == LibraryStatus.pending:
                service = build_extraction_service(session, settings)
            else:
                service = build_compression_service(session, settings)

            await service.run(library)
            await session.refresh(library)
            logger.info(
                "Processed library_id=%s status_before=%s status_after=%s "
                "error_message=%s",
                library.id,
                status_before,
                library.status.value,
                library.error_message,
            )
    except Exception:
        logger.exception(
            "Unexpected worker error for library_id=%s expected_status=%s",
            library_id,
            expected_status.value,
        )


async def process_pending(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Config,
) -> None:
    library_ids = await _library_ids_by_status(session_factory, LibraryStatus.pending)
    for library_id in library_ids:
        await _process_library(
            session_factory,
            library_id,
            LibraryStatus.pending,
            settings,
        )


async def process_extracted(
    session_factory: async_sessionmaker[AsyncSession],
    settings: Config,
) -> None:
    library_ids = await _library_ids_by_status(session_factory, LibraryStatus.extracted)
    for library_id in library_ids:
        await _process_library(
            session_factory,
            library_id,
            LibraryStatus.extracted,
            settings,
        )


async def run_worker_loop(worker_settings: Config) -> None:
    while True:
        await process_pending(async_session_maker, worker_settings)
        await process_extracted(async_session_maker, worker_settings)
        await asyncio.sleep(worker_settings.WORKER_POLL_INTERVAL_SECONDS)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(run_worker_loop(settings))


if __name__ == "__main__":
    main()
