import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from starlette.datastructures import UploadFile

from app.core.security.deps import CurrentUser, get_current_user
from app.repositories.extractors.dispatcher import FILE_TYPE_BY_EXTENSION
from app.schemas.knowledge import (
    KnowledgeCreateSchema,
    KnowledgeResponseSchema,
    KnowledgeUpdateSchema,
)
from app.schemas.library import (
    LibraryResponseSchema,
    LibraryUrlCreateSchema,
    build_minio_key,
)
from app.services.knowledge import KnowledgeService
from app.services.library import LibraryService
from app.use_cases.library import get_knowledge_service, get_library_service


api_v1_router = APIRouter(prefix="/api/v1")


@api_v1_router.post(
    "/knowledge", response_model=KnowledgeResponseSchema, status_code=status.HTTP_201_CREATED
)
async def create_knowledge(
    payload: KnowledgeCreateSchema,
    current_user: CurrentUser = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeResponseSchema:
    return await service.create(
        user_id=current_user.user_id,
        title=payload.title,
        description=payload.description,
    )


@api_v1_router.get("/knowledge", response_model=list[KnowledgeResponseSchema])
async def list_knowledge(
    current_user: CurrentUser = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> list[KnowledgeResponseSchema]:
    return await service.list_for_user(current_user.user_id)


@api_v1_router.get("/knowledge/{knowledge_id}", response_model=KnowledgeResponseSchema)
async def get_knowledge(
    knowledge_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeResponseSchema:
    return await service.get_owned_or_raise(knowledge_id, current_user.user_id)


@api_v1_router.patch("/knowledge/{knowledge_id}", response_model=KnowledgeResponseSchema)
async def update_knowledge(
    knowledge_id: uuid.UUID,
    payload: KnowledgeUpdateSchema,
    current_user: CurrentUser = Depends(get_current_user),
    service: KnowledgeService = Depends(get_knowledge_service),
) -> KnowledgeResponseSchema:
    return await service.update(
        knowledge_id=knowledge_id,
        user_id=current_user.user_id,
        title=payload.title,
        description=payload.description,
    )


@api_v1_router.delete("/knowledge/{knowledge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge(
    knowledge_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service),
) -> Response:
    await service.delete_knowledge_owned(knowledge_id, current_user.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@api_v1_router.post(
    "/knowledge/{knowledge_id}/libraries",
    response_model=LibraryResponseSchema,
    status_code=status.HTTP_201_CREATED,
)
async def create_library(
    knowledge_id: uuid.UUID,
    request: Request,
    current_user: CurrentUser = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service),
) -> LibraryResponseSchema:
    content_type = request.headers.get("content-type", "").lower()
    if content_type.startswith("multipart/form-data"):
        await service.get_knowledge_owned_or_raise(knowledge_id, current_user.user_id)
        form = await request.form()
        uploaded_file = form.get("file")
        if not isinstance(uploaded_file, UploadFile):
            raise HTTPException(status_code=422, detail="multipart field 'file' is required")

        filename = Path(uploaded_file.filename or "").name
        extension = Path(filename).suffix.lower().lstrip(".")
        if not extension or extension not in FILE_TYPE_BY_EXTENSION:
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail="unsupported file extension",
        )

        form_title = form.get("title")
        title = (
            form_title.strip()
            if isinstance(form_title, str) and form_title.strip()
            else filename
        )
        object_key = build_minio_key(current_user.user_id, uuid.uuid4(), extension)
        await service.upload_document(
            uploaded_file.file,
            object_key,
            uploaded_file.content_type,
        )
        return await service.create_from_file(
            knowledge_id=knowledge_id,
            user_id=current_user.user_id,
            original_ref=object_key,
            title=title,
        )

    if content_type.startswith("application/json"):
        payload: dict[str, Any] = await request.json()
        try:
            url_payload = LibraryUrlCreateSchema.model_validate(payload)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="JSON field 'url' is required") from exc
        return await service.create_from_url(
            knowledge_id=knowledge_id,
            user_id=current_user.user_id,
            url=url_payload.url,
            title=url_payload.title,
        )

    raise HTTPException(
        status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        detail="use multipart/form-data with file or application/json with url",
    )


@api_v1_router.get(
    "/knowledge/{knowledge_id}/libraries", response_model=list[LibraryResponseSchema]
)
async def list_libraries(
    knowledge_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service),
) -> list[LibraryResponseSchema]:
    return await service.list_for_knowledge(knowledge_id, current_user.user_id)


@api_v1_router.get("/libraries/{library_id}", response_model=LibraryResponseSchema)
async def get_library(
    library_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service),
) -> LibraryResponseSchema:
    return await service.get_owned_or_raise(library_id, current_user.user_id)


@api_v1_router.delete("/libraries/{library_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_library(
    library_id: uuid.UUID,
    current_user: CurrentUser = Depends(get_current_user),
    service: LibraryService = Depends(get_library_service),
) -> Response:
    await service.delete_owned(library_id, current_user.user_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
