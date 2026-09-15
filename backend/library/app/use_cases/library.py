from app.core.config import settings
from app.db.session import SessionDep
from app.repositories.knowledge import KnowledgeRepository
from app.repositories.library import LibraryRepository
from app.repositories.library_chunk import LibraryChunkRepository
from app.services.knowledge import KnowledgeService
from app.services.library import LibraryService
from app.storage.document_storage import DocumentStorage


def get_knowledge_service(session: SessionDep) -> KnowledgeService:
    return KnowledgeService(KnowledgeRepository(session))


def get_library_service(session: SessionDep) -> LibraryService:
    return LibraryService(
        library_repository=LibraryRepository(session),
        knowledge_repository=KnowledgeRepository(session),
        chunk_repository=LibraryChunkRepository(session),
        storage=DocumentStorage(settings),
        session=session,
    )
