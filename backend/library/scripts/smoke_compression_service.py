"""Manually exercise CompressionService with an extracted Library row.

Run in the library container with OPENAI_API_KEY configured:
    docker compose exec library python scripts/smoke_compression_service.py
"""

import asyncio
import uuid

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.library import SourceType, LibraryStatus
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.library import LibraryRepository
from app.services.compression import CompressionService
from app.use_cases.compression import build_compression_service


async def main() -> None:
    async with async_session_maker() as session:
        knowledge_repo = KnowledgeRepository(session)
        library_repo = LibraryRepository(session)

        knowledge = await knowledge_repo.create(
            user_id=uuid.uuid4(),
            title="Compression service smoke test",
        )
        library = await library_repo.create(
            knowledge_id=knowledge.id,
            source_type=SourceType.file,
            original_ref="smoke/compression-source.txt",
        )
        await library_repo.update_content(
            library,
            text_content=(
                "Конспект должен сохранять ключевые факты и связи. "
                "Сжатие не должно добавлять информацию, которой нет в источнике."
            ),
        )
        await library_repo.update_status(library, LibraryStatus.extracted)

        service = build_compression_service(session, settings)
        print(f"factory result: {type(service).__name__}")
        assert isinstance(service, CompressionService)
        print(f"factory agent: {type(service.agent).__name__}")
        print(f"status before: {library.status.value}")

        await service.run(library)
        final_library = await library_repo.get_by_id(library.id)

    assert final_library is not None
    print(f"status after: {final_library.status.value}")
    if final_library.status == LibraryStatus.compressed:
        print(f"compressed_content chars: {len(final_library.compressed_content or '')}")
        print(f"compressed_content:\n{final_library.compressed_content}")
    else:
        print(f"error_message: {final_library.error_message}")


if __name__ == "__main__":
    asyncio.run(main())
