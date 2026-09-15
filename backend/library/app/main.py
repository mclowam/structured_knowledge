from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.api.library import api_v1_router
from app.services.errors import (
    KnowledgeAccessDeniedError,
    KnowledgeNotFoundError,
    LibraryNotFoundError,
)

app = FastAPI()

app.include_router(api_v1_router)


@app.exception_handler(KnowledgeNotFoundError)
async def knowledge_not_found_handler(
    _: Request, __: KnowledgeNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "knowledge not found"})


@app.exception_handler(KnowledgeAccessDeniedError)
async def knowledge_access_denied_handler(
    _: Request, __: KnowledgeAccessDeniedError
) -> JSONResponse:
    return JSONResponse(status_code=403, content={"detail": "knowledge access denied"})


@app.exception_handler(LibraryNotFoundError)
async def library_not_found_handler(
    _: Request, __: LibraryNotFoundError
) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "library not found"})

@app.get("/health")
def health():
    return {"status": "OK"}
