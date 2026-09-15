from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.compression import CompressionAgent
from app.core.config import Config
from app.services.compression import CompressionService


def build_compression_service(
    session: AsyncSession,
    settings: Config,
) -> CompressionService:
    return CompressionService(
        session=session,
        agent=CompressionAgent(settings),
    )
