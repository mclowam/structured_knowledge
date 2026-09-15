from typing import Protocol, runtime_checkable
from app.schemas.library import ExtractedContent


@runtime_checkable
class IFileExtractor(Protocol):
    async def extract(self, local_path: str) -> ExtractedContent: ...


@runtime_checkable
class IUrlExtractor(Protocol):
    async def extract(self, url: str) -> ExtractedContent: ...