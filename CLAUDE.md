# Structured Knowledge

## Scope and boundaries

The repository contains two independent FastAPI services:

- `backend/auth` owns users and JWT authentication.
- `backend/library` owns knowledge bases, library sources, extracted text, and chunks.

Both services have an `app` package. Always run Python, Alembic, and test commands from the selected service directory. Never import `app` modules across the services.

When a task is scoped to one service, do not edit the other service or its migrations.

## Local stack

`docker-compose.yml` starts:

| Service | Host port | Dependencies |
| --- | --- | --- |
| `auth` | `8001` | `auth-postgres` |
| `library` | `8002` | `library-postgres`, `minio` |
| MinIO API / console | `9000` / `9001` | `library-network` |

```powershell
docker compose up --build
```

Both services mount their source directory into `/service`. Their Dockerfiles run `uvicorn app.main:app --host 0.0.0.0 --port 8000`.

`.env` files are local and ignored by Git. Do not commit or print secrets. Use the corresponding `.env.example` as the source of non-secret development settings. In the `library` container, MinIO must be addressed as `http://minio:9000`, not a host `localhost` port.

## Common verification

Run these from the relevant service directory:

```powershell
python -m compileall app
alembic upgrade head
```

Basic health checks:

```powershell
Invoke-RestMethod http://localhost:8001/health
Invoke-RestMethod http://localhost:8002/health
```

Use a new Alembic migration for ORM schema changes; do not modify an already-applied initial migration.

## Auth service

`backend/auth` exposes registration, login, refresh, user lookup, and `/me`. The intended layering is:

```text
route -> dependency/factory -> service -> repository -> AsyncSession
```

Routes must not run SQL directly. Repositories must not raise `HTTPException`. Auth domain failures need explicit HTTP mapping in the API layer.

## Library service

`backend/library` currently exposes only `GET /health` over HTTP. Its domain and extraction code can be used without an HTTP layer through factories in `app/use_cases/extraction.py`:

```python
from app.use_cases.extraction import build_extraction_service

service = build_extraction_service(session, settings)
await service.run(library)
```

`build_extraction_dispatcher(settings)` creates one MinIO-backed dispatcher and real PDF, DOCX, media, webpage, and YouTube extractors. `MediaExtractor` loads a Whisper model when constructed; do not create it in a request path unless that startup cost is acceptable.

### Extraction lifecycle

```text
Library(pending)
  -> ExtractionService.run
  -> extracting
  -> dispatcher
       file: MinIO -> temporary file -> PDF / DOCX / media extractor
       URL: webpage / YouTube extractor
  -> extracted | failed
```

- Failures are persisted in `Library.status=failed` with `error_message`.
- A discovered title fills an empty `Library.title`.
- Text up to 4,000 characters is stored in `Library.text_content`.
- Longer text is split into `library_chunk` rows. Existing chunks are deleted before replacement.
- Re-running extraction must not accumulate chunks.
- YouTube first attempts VTT subtitles via `yt-dlp` and `webvtt-py`; unavailable or unparsable subtitles fall back to media/STT.

The library image requires `ffmpeg` for media/video extraction. Python dependencies live in UTF-8 `backend/library/requirements.txt`.

### Manual smoke test

The repository includes `backend/library/tests/fixtures/smoke.pdf` and a non-pytest script. With the stack and migrations ready:

```powershell
docker compose exec -T `
  -e MINIO_ENDPOINT=http://minio:9000 `
  -e MINIO_ACCESS_KEY=<local MinIO access key> `
  -e MINIO_SECRET_KEY=<local MinIO secret key> `
  library python scripts/smoke_extraction.py
```

It creates a test `Knowledge`, uploads a small PDF to MinIO, creates a `Library`, invokes `ExtractionService.run()`, and prints final status, text content, chunk count, and an error message for failures.

## Data ownership and design rules

- Library operations that access a knowledge base must validate ownership through `KnowledgeService.get_owned_or_raise`.
- A future library HTTP layer must obtain the user identity from a trusted auth context, not a request-body `user_id`.
- Keep source upload/storage, extraction, and persistence separated: route -> service -> repository.
- Keep temporary-file cleanup in `finally` blocks and preserve the extraction status transition on every failure.

## Known TODOs (not implemented)

- No Library HTTP API, auth integration, job queue, or background worker exists yet.
- Foreign keys do not use `ON DELETE CASCADE`; deletion of Knowledge/Library needs an explicit cascade strategy.
- `WebpageExtractor` needs SSRF protections, redirect/IP validation, response-size limits, and stricter time budgets before production exposure.
- `object_proxy()` targets an endpoint that is not implemented.
- PDF extraction does not perform OCR; scanned PDFs become `EmptyTextLayerError`.

## Working-tree hygiene

- Preserve unrelated dirty changes; never use `git reset --hard` or discard user work.
- Commit only files that belong to the requested change.
- Do not add `.env`, generated caches, local virtual environments, or secrets to Git.
