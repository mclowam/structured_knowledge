import asyncio
import uuid
from pathlib import Path

from botocore.exceptions import ClientError

from app.core.config import settings, session_minio
from app.db.session import async_session_maker
from app.models.library import LibraryStatus, SourceType
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.library import LibraryRepository
from app.storage.document_storage import DocumentStorage
from app.worker import process_extracted, process_pending

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
    document_key = f"smoke/worker-{uuid.uuid4()}.pdf"
    with FIXTURE_PATH.open("rb") as fixture:
        await DocumentStorage(settings).upload_document(
            fixture,
            document_key,
            "application/pdf",
        )

    async with async_session_maker() as session:
        knowledge_repo = KnowledgeRepository(session)
        library_repo = LibraryRepository(session)
        knowledge = await knowledge_repo.create(
            user_id=uuid.uuid4(),
            title="Worker smoke test",
        )
        pending_library = await library_repo.create(
            knowledge_id=knowledge.id,
            source_type=SourceType.file,
            original_ref=document_key,
        )
        extracted_library = await library_repo.create(
            knowledge_id=knowledge.id,
            source_type=SourceType.file,
            original_ref="smoke/worker-extracted.txt",
        )
        await library_repo.update_content(
            extracted_library,
            text_content=(
                "Сжатие сохраняет ключевые факты. "
                "Связный конспект не добавляет сведения вне источника."
            ),
        )
        await library_repo.update_status(extracted_library, LibraryStatus.extracted)
        print(
            f"pending library_id={pending_library.id} "
            f"status before={pending_library.status.value}"
        )
        print(
            f"extracted library_id={extracted_library.id} "
            f"status before={extracted_library.status.value}"
        )

    await process_pending(async_session_maker, settings)
    await process_extracted(async_session_maker, settings)

    async with async_session_maker() as session:
        library_repo = LibraryRepository(session)
        pending_final = await library_repo.get_by_id(pending_library.id)
        extracted_final = await library_repo.get_by_id(extracted_library.id)

    assert pending_final is not None
    assert extracted_final is not None
    for label, library in (
        ("pending", pending_final),
        ("extracted", extracted_final),
    ):
        print(f"{label} library_id={library.id} status after={library.status.value}")
        if library.status == LibraryStatus.failed:
            print(f"{label} error_message={library.error_message}")
        if library.compressed_content:
            print(
                f"{label} compressed_content chars="
                f"{len(library.compressed_content)}"
            )


if __name__ == "__main__":
    asyncio.run(main())
