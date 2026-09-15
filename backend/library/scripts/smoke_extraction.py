"""Manually exercise the PDF extraction path against the running library stack.

Run from the repository root after `docker compose up -d` and migrations:
    docker compose exec library python scripts/smoke_extraction.py
"""

import asyncio
import uuid
from pathlib import Path

from botocore.exceptions import ClientError

from app.core.config import settings, session_minio
from app.db.session import async_session_maker
from app.models.library import SourceType
from app.repositories.extractors.chunker import TextChunker
from app.repositories.extractors.dispatcher import ExtractionDispatcher
from app.repositories.extractors.pdf import PdfExtractor
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.library import LibraryRepository
from app.repositories.library_chunk import LibraryChunkRepository
from app.services.extraction import ExtractionService
from app.storage.document_storage import DocumentStorage

FIXTURE_PATH = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "smoke.pdf"


async def ensure_bucket() -> None:
    async with session_minio.client(
        "s3",
        endpoint_url=settings.MINIO_ENDPOINT,
        aws_access_key_id=settings.MINIO_ACCESS_KEY,
        aws_secret_access_key=settings.MINIO_SECRET_KEY,
    ) as s3:
        try:
            await s3.head_bucket(Bucket=settings.MINIO_BUCKET)
        except ClientError as error:
            if error.response["Error"].get("Code") not in {"404", "NoSuchBucket"}:
                raise
            await s3.create_bucket(Bucket=settings.MINIO_BUCKET)


async def main() -> None:
    if not FIXTURE_PATH.is_file():
        raise FileNotFoundError(f"Smoke-test fixture is missing: {FIXTURE_PATH}")

    await ensure_bucket()
    storage = DocumentStorage(settings)
    document_key = f"smoke/{uuid.uuid4()}.pdf"
    with FIXTURE_PATH.open("rb") as fixture:
        await storage.upload_document(fixture, document_key, "application/pdf")

    async with async_session_maker() as session:
        knowledge_repo = KnowledgeRepository(session)
        library_repo = LibraryRepository(session)
        chunk_repo = LibraryChunkRepository(session)

        knowledge = await knowledge_repo.create(
            user_id=uuid.uuid4(),
            title="Extraction smoke test",
        )
        library = await library_repo.create(
            knowledge_id=knowledge.id,
            source_type=SourceType.file,
            original_ref=document_key,
        )
        dispatcher = ExtractionDispatcher(
            storage=storage,
            file_extractors={"pdf": PdfExtractor()},
            url_extractors={},
        )
        service = ExtractionService(
            dispatcher=dispatcher,
            chunker=TextChunker(),
            library_repo=library_repo,
            chunk_repo=chunk_repo,
        )

        await service.run(library)
        final_library = await library_repo.get_by_id(library.id)
        chunks = await chunk_repo.list_by_library(library.id)

    assert final_library is not None
    print(f"Library.status: {final_library.status.value}")
    print(f"text_content: {final_library.text_content!r}")
    print(f"chunk count: {len(chunks)}")
    if final_library.status.value == "failed":
        print(f"error_message: {final_library.error_message}")


if __name__ == "__main__":
    asyncio.run(main())
