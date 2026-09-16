# Structured Knowledge — operating guide for code agents

This file is a factual map of the repository as it exists now. Use it to
diagnose a problem before changing code. Do not infer a feature from a model,
an old issue, or a file name: follow the actual request path described below.

## Scope and non-negotiable boundaries

This repository has two **independent** FastAPI services:

| Service | Directory | Owns | Database | Host port |
| --- | --- | --- | --- | --- |
| Auth | `backend/auth` | users, passwords, JWT issuance/refresh | `auth_db` | `8001` |
| Library | `backend/library` | knowledge, sources, extraction, chunks, summaries | `library_db` | `8002` |

Both services contain a top-level Python package named `app`. They are not a
shared Python application.

- Run Python, Alembic, and local commands from the target service directory.
- Never import `app.*` across service boundaries.
- A task scoped to `backend/library` must not change Auth source code, and vice
  versa, unless the task explicitly asks for a cross-service change.
- Preserve unrelated dirty working-tree changes.
- Do not commit `.env` files, real secrets, tokens, model caches, generated
  output, virtual environments, or `__pycache__`.
- Add a new Alembic revision for a schema change; do not rewrite an applied
  migration.

The intended application layer is:

```text
FastAPI route -> dependency/factory -> domain service -> repository -> AsyncSession
```

Routes must not execute SQL. Repositories must not raise `HTTPException`.
Domain exceptions are converted to HTTP responses only in the application
handler layer.

## Infrastructure

The root `docker-compose.yml` declares:

| Compose service | Container | Ports | Network | Depends on |
| --- | --- | --- | --- | --- |
| `auth` | `knowledge_auth` | `8001:8000` | `auth-network` | `auth-postgres` |
| `library` | `knowledge_library` | `8002:8000` | `library-network` | `library-postgres`, `minio` |
| `auth-postgres` | `knowledge_auth_pg` | `5433:5432` | `auth-network` | — |
| `library-postgres` | `knowledge_library_pg` | `5434:5432` | `library-network` | — |
| `minio` | `knowledge_library_minio` | API `9000`, console `9001` | `library-network` | — |

Both source directories are bind-mounted at `/service`. Dockerfiles start
Uvicorn without reload. Rebuild the affected image when `requirements.txt` or
a Dockerfile changes; bind mounts do not install a new dependency in a running
container.

```powershell
Set-Location C:\structured_knowledge
docker compose up --build -d
docker compose ps
Invoke-RestMethod http://localhost:8001/health
Invoke-RestMethod http://localhost:8002/health
```

### Environment rules

Real `.env` files are ignored and must never be printed. Use
`backend/library/.env.example` only as the tracked list of names.

`backend/library/app/core/config.py` constructs `settings = Config()` at
import time. Therefore a missing required variable prevents importing the
Library app, worker, or scripts.

| Library variable | Required | Runtime purpose |
| --- | --- | --- |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | no | Database connection; Compose overrides host/port inside containers. |
| `MINIO_ENDPOINT` | no | Must point to `http://minio:9000` inside Compose, never host-only `localhost:9100`. |
| `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET` | no | S3-compatible credentials and bucket. Credentials must match `minio` service configuration in root compose. |
| `AUTH_SECRET_KEY` | **yes** | Must equal Auth's `SECRET_KEY`. Library uses it to locally validate Auth access JWTs. |
| `OPENAI_API_KEY` | **yes** | Required even for imports because `Config` validates it at import time. |
| `COMPRESSION_MODEL` | no | Defaults to `gpt-5-mini`. |
| `WORKER_POLL_INTERVAL_SECONDS` | no | Defaults to `10`. |

The shared-secret JWT design is an MVP convenience. It is not a production
trust boundary; a production replacement should use asymmetric JWTs or token
introspection. Do not add an HTTP call from Library to Auth unless a task
explicitly asks for that architecture.

After changing an `env_file`, recreate the service so the running container
receives the new environment:

```powershell
docker compose up -d --force-recreate library
```

## Auth service

### Paths and behavior

`backend/auth/app/main.py` includes an `APIRouter(prefix="/auth")`, so the
public Auth endpoints are:

| Method | Path | Authentication | Result |
| --- | --- | --- | --- |
| `GET` | `/health` | no | `{"status":"OK"}` |
| `POST` | `/auth/register` | no | Create user; `201`. |
| `POST` | `/auth/login` | no | Access and refresh tokens. |
| `POST` | `/auth/refresh` | no | New access/refresh pair; invalid or expired refresh token is `401`. |
| `GET` | `/auth/me` | access Bearer | Current token payload. |
| `GET` | `/auth/users` | access Bearer | User list; no staff-only rule currently. |
| `GET` | `/auth/users/{user_id}` | access Bearer | One user. |

Key locations:

- `app/api/users.py` — routes.
- `app/use_cases/users.py` — service dependencies.
- `app/core/security/token.py` — `JWTTokenProvider`.
- `app/core/security/deps.py` — `get_current_user` dependency.
- `app/services/{register,login,refresh,users}.py` — application flows.

### JWT contract shared with Library

Auth uses PyJWT, algorithm `HS256`, and `SECRET_KEY` from Auth configuration.
`JWTTokenProvider.create_access_token()` produces a token with these relevant
claims:

```text
type="access"
user_id=<UUID string>
username=<string>
is_staff=<bool>
iat, exp, jti
```

Refresh tokens instead use `type="refresh"` and `sub=<UUID string>`. A refresh
token is not accepted by the current-user dependency. Access expiry is 15
minutes; refresh expiry is 30 days. Refresh tokens are not persisted or
revoked.

Library mirrors this format in
`backend/library/app/core/security/deps.py`; it decodes with
`AUTH_SECRET_KEY`, requires `type == "access"`, and validates `user_id` and
`username`. Library must not import Auth code to do this.

## Library service

### Directory map

```text
backend/library/
├── app/
│   ├── api/library.py                 # HTTP API, prefix /api/v1
│   ├── agents/compression.py          # Async OpenAI compression agent
│   ├── abstractions/                  # repository/extractor protocols
│   ├── core/{config.py,security/deps.py}
│   ├── db/{base.py,session.py}
│   ├── models/{knowledge,library,library_chunk}.py
│   ├── repositories/
│   │   ├── {knowledge,library,library_chunk}.py
│   │   └── extractors/{chunker,dispatcher,docs,media,pdf,webpage,youtube}.py
│   ├── services/{knowledge,library,extraction,compression,errors}.py
│   ├── storage/{document_storage,object_proxy}.py
│   ├── use_cases/{library,extraction,compression}.py
│   └── worker.py                      # standalone polling process
├── scripts/                           # manual smoke scripts only; not CI
├── tests/fixtures/smoke.pdf
├── migrations/versions/2b55a08b8580_init_models.py
└── requirements.txt
```

`app/main.py` mounts `api_v1_router` and registers domain exception handlers:

- `KnowledgeNotFoundError` -> `404`.
- `KnowledgeAccessDeniedError` -> `403`.
- `LibraryNotFoundError` -> `404`.

### Data model and state machine

```text
Knowledge (one owner user_id)
    └── Library (source file or URL)
            └── LibraryChunk (zero-based order)
```

| Model | Key fields |
| --- | --- |
| `Knowledge` | UUID `id`, UUID `user_id`, title, optional description, timestamps. |
| `Library` | UUID `id`, `knowledge_id`, `source_type`, `original_ref`, optional title, status, error, raw/compressed text, optional order, timestamps. |
| `LibraryChunk` | UUID `id`, `library_id`, integer `order`, text. |

```text
SourceType:    file | url
LibraryStatus: pending -> extracting -> extracted -> compressing -> compressed
                         \-> failed       \-> failed
```

`quiz_ready` exists in the enum but no quiz flow exists. The schema has foreign
keys but no ORM relationships and no `ON DELETE CASCADE`; deletion is explicit
application logic.

## Library HTTP API

Base URL: `http://localhost:8002/api/v1`.

Except `GET /health`, each route requires an Auth **access** token in
`Authorization: Bearer <token>`. User identity always comes from the JWT;
never accept an owner/user ID from a request body or query string.

| Method | Path | Input | Behavior |
| --- | --- | --- | --- |
| `POST` | `/knowledge` | JSON `{title, description?}` | Create knowledge owned by caller; `201`. |
| `GET` | `/knowledge` | — | List caller's knowledge. |
| `GET` | `/knowledge/{knowledge_id}` | — | Fetch owned Knowledge. |
| `PATCH` | `/knowledge/{knowledge_id}` | JSON `{title?, description?}` | Update owned Knowledge. |
| `DELETE` | `/knowledge/{knowledge_id}` | — | Delete owned Knowledge, all children/chunks, and MinIO file objects; `204`. |
| `POST` | `/knowledge/{knowledge_id}/libraries` | multipart `file`, or JSON `{url, title?}` | Create pending source; `201`. |
| `GET` | `/knowledge/{knowledge_id}/libraries` | — | List sources belonging to owned Knowledge. |
| `GET` | `/libraries/{library_id}` | — | Fetch owned source, including text/compression/error fields. |
| `DELETE` | `/libraries/{library_id}` | — | Delete chunks, source, and (for files) MinIO object; `204`. |

The create-source route branches by `Content-Type`:

- `multipart/form-data`, field name exactly `file`: uploads to MinIO first,
  creates `Library(source_type=file, original_ref=<object key>, status=pending)`.
  Filename becomes the initial title.
- `application/json`: field `url` is required; creates
  `Library(source_type=url, original_ref=<url>, status=pending)` without MinIO.
- Any other content type receives `415`.

No file size/type validation, quota, rate limiting, quiz API, or automatic
worker Compose service is implemented.

### API construction and ownership path

```text
app/api/library.py
  -> get_current_user()              # local PyJWT validation
  -> get_knowledge_service() / get_library_service()
  -> KnowledgeService / LibraryService
  -> repositories + AsyncSession
```

Factories are in `app/use_cases/library.py`. They construct `DocumentStorage`
with the singleton `settings`, so the HTTP upload path and extraction path use
the same config object shape.

Ownership rules:

- `KnowledgeService.get_owned_or_raise()` loads by id, then compares its
  `user_id` to the JWT identity.
- `LibraryService.get_owned_or_raise()` loads Library, then delegates ownership
  to the parent Knowledge.
- Do not bypass either service in a route.

Deletion is deliberately explicit. `LibraryService.delete_owned()` deletes a
file object when appropriate, deletes its chunks and Library without interim
commits, then commits once. `delete_knowledge_owned()` does the equivalent for
all child sources and then deletes Knowledge in one database transaction.
An external MinIO deletion cannot participate in a PostgreSQL transaction;
failure handling is best effort and must be considered when hardening this for
production.

## DocumentStorage and MinIO diagnosis

`DocumentStorage` is the only S3 adapter. It is used by both the HTTP upload
flow and extraction dispatching:

```text
HTTP multipart POST
  app/api/library.py -> LibraryService.upload_document()
  -> DocumentStorage.upload_document()

Extraction of SourceType.file
  ExtractionDispatcher._extract_file()
  -> DocumentStorage.get_bytes()
```

The client setup in `app/storage/document_storage.py` is intentionally the
same for `upload_document()`, `get_bytes()`, and `delete_object()`:

```python
session_minio = aioboto3.Session()   # one module-global session
session_minio.client(
    "s3",
    endpoint_url=settings.MINIO_ENDPOINT,
    aws_access_key_id=settings.MINIO_ACCESS_KEY,
    aws_secret_access_key=settings.MINIO_SECRET_KEY,
)
```

Each operation opens its own short-lived client context, but all use the same
module-global `aioboto3.Session` and identical three connection arguments.
`region_name` and S3 `addressing_style` are intentionally unset in all three
paths. Do not change only upload or only download client options: that creates
an artificial read/write discrepancy.

### Diagnose a file upload failure in this order

1. Compare `backend/library/.env` with the `minio` service environment in root
   `docker-compose.yml`. Do not print values. Confirm endpoint, access key, and
   secret key match the MinIO service configuration, and bucket is nonempty.
2. Recreate `library` after editing `.env`.
3. Inspect the **running container**, not only the file. This safe PowerShell
   check compares the credentials without printing them; it outputs only a
   Boolean. Do not save the temporary variables to a file or transcript:

   ```powershell
   $librarySecret = (docker compose exec -T library printenv MINIO_SECRET_KEY).Trim()
   $minioSecret = (docker compose exec -T minio printenv MINIO_ROOT_PASSWORD).Trim()
   "MINIO_SECRET_KEY_matches_minio=$($librarySecret -ceq $minioSecret)"
   Remove-Variable librarySecret, minioSecret

   docker compose exec -T library python -c "import os; print('MINIO_ENDPOINT=' + os.getenv('MINIO_ENDPOINT', '<missing>')); print('MINIO_BUCKET=' + os.getenv('MINIO_BUCKET', '<missing>')); print('MINIO_ACCESS_KEY_present=' + str(bool(os.getenv('MINIO_ACCESS_KEY')))); print('MINIO_SECRET_KEY_present=' + str(bool(os.getenv('MINIO_SECRET_KEY'))))"
   ```

4. A connection attempt to `localhost:9100` from the Library container means
   the container has a stale/wrong endpoint. Containers on the Compose network
   must use the service DNS name `minio` and port `9000`.
5. A `403`, `InvalidAccessKeyId`, or `SignatureDoesNotMatch` after reaching
   `minio:9000` indicates credentials differ between Library and MinIO.
6. A missing-bucket response means create the configured bucket first; storage
   deliberately does not create it automatically.

The `scripts/smoke_extraction.py` and `scripts/smoke_worker.py` helpers ensure
the bucket exists before uploading their fixtures. The HTTP upload API does
not; provision the bucket as deployment setup.

## Extraction pipeline

### Construction

`app/use_cases/extraction.py` exposes:

```python
build_extraction_dispatcher(settings) -> ExtractionDispatcher
build_extraction_service(session, settings) -> ExtractionService
```

It wires `DocumentStorage`, `PdfExtractor`, `DocxExtractor`, `WebpageExtractor`,
`YoutubeExtractor`, `TextChunker`, and repository instances.

`LazyMediaExtractor` is shared by audio, video, and YouTube fallback. It does
not construct `MediaExtractor`/Faster-Whisper until `.extract()` is called for
media. Thus a PDF/DOCX extraction does not download or initialize Whisper.

### Dispatching

For a file, `ExtractionDispatcher` uses the extension in `Library.original_ref`,
downloads it from MinIO to a temporary file, invokes the extractor, and removes
the temporary file in `finally`.

| Extensions | Extractor |
| --- | --- |
| `pdf` | `PdfExtractor` / `pypdf` |
| `docx` | `DocxExtractor` / `python-docx` |
| `mp3`, `wav`, `m4a` | lazy `MediaExtractor` |
| `mp4`, `mov`, `mkv` | lazy `MediaExtractor` with `ffmpeg` audio extraction |

For URLs, YouTube hostnames select `YoutubeExtractor`; all other URLs select
`WebpageExtractor`.

- PDF extractor raises `EmptyTextLayerError` for an insufficient text layer;
  no OCR exists.
- Webpage extractor uses `httpx` + `trafilatura`.
- Media extractor runs `ffmpeg` then Faster-Whisper (`small`, CPU int8).
- YouTube first attempts `yt-dlp` VTT captions (`webvtt-py` parsing); malformed
  captions return `None`, then extraction falls back to audio/STT.

### ExtractionService persistence

`ExtractionService.run(library)`:

1. Writes `extracting`.
2. Dispatches extraction.
3. On any extraction error, writes `failed` plus `str(error)` and returns.
4. Copies `ExtractedContent.title` only when `Library.title` is empty.
5. For text `<= CHUNK_THRESHOLD_CHARS` (currently 4000), stores
   `Library.text_content`.
6. For longer text, deletes existing chunks, splits with `TextChunker`, then
   writes replacement chunks.
7. Writes `extracted`.

The 4000-character extraction threshold is a database-storage decision. It is
not the compression model context threshold.

## Compression pipeline

`CompressionAgent` (`app/agents/compression.py`) is a thin async OpenAI SDK
wrapper. It has no DB access, retries, cache, token accounting, provider
abstraction, or concurrent map processing.

```python
CompressionAgent(settings: Config, model: str | None = None)
await agent.compress(text: str) -> str
```

- Empty/whitespace text raises `ValueError` before an OpenAI call.
- Text below `COMPRESSION_MAP_REDUCE_THRESHOLD_CHARS = 4000` gets one request.
- Longer text uses `TextChunker(max_chunk_words=800)`, compresses pieces
  **sequentially**, then makes a separate reduce request.
- Map and reduce prompts are different constants.
- `last_chunk_count` exposes the prior long-text chunk count for smoke output.

`CompressionService.run(library)` only accepts `extracted` sources. It writes
`compressing`, uses nonblank `text_content` or ordered chunks, invokes the
agent, then `complete_compression()` writes output plus `compressed` in one
repository commit. Any failure after start is recorded as `failed` with
`error_message`.

Build through `app/use_cases/compression.py`:

```python
service = build_compression_service(session, settings)
```

## Polling worker

`backend/library/app/worker.py` is a standalone asyncio process. Compose does
not start a separate worker service.

```powershell
Set-Location C:\structured_knowledge\backend\library
python -m app.worker
```

Its loop:

1. Selects IDs with status `pending`; each is reloaded in an isolated session
   and sent to a newly built `ExtractionService`.
2. Selects IDs with status `extracted`; each is reloaded in an isolated session
   and sent to a newly built `CompressionService`.
3. Sleeps for `WORKER_POLL_INTERVAL_SECONDS`.

The same tick can extract a pending source and compress it afterward. The
worker catches/logs unexpected errors per Library and continues with later
items. It has no queue, row lock, distributed coordination, graceful shutdown,
or metrics; do not run multiple workers without solving duplicate work.

## Manual checks

Run these manually; they are not CI.

| Script | Scope | Invocation |
| --- | --- | --- |
| `scripts/smoke_extraction.py` | fixture PDF -> extraction + chunks | `docker compose exec -T library python scripts/smoke_extraction.py` |
| `scripts/smoke_compression.py` | OpenAI agent short and map-reduce paths; no DB/MinIO | from `backend/library`: `python scripts/smoke_compression.py` |
| `scripts/smoke_compression_service.py` | DB-backed CompressionService | `docker compose exec -T library python scripts/smoke_compression_service.py` |
| `scripts/smoke_worker.py` | one extraction and compression worker pass | `docker compose exec -T library python scripts/smoke_worker.py` |

For a manual HTTP flow:

1. `POST /auth/login` on port 8001 and save `access_token`.
2. `POST /api/v1/knowledge` on port 8002 with the Bearer token.
3. `POST /api/v1/knowledge/{id}/libraries` as JSON URL or multipart field
   `file` using `tests/fixtures/smoke.pdf`; expect `201` and `pending`.
4. Run `python -m app.worker` in the Library container/process.
5. `GET /api/v1/libraries/{id}` until `compressed` or `failed`.
6. Exercise a request without token (`401`), a request by a different user
   (`403`), and `DELETE /knowledge/{id}` followed by GET (`404`).

## Known limitations — record, do not silently fix

1. **Web SSRF:** `WebpageExtractor` accepts user-controlled URLs without
   private-network filtering, redirect controls, or response-size limits.
2. **No OCR:** scanned/image-only PDFs fail text extraction.
3. **MinIO bucket lifecycle:** HTTP uploads do not create a missing bucket.
4. **MinIO vs DB atomicity:** file object deletion and database deletion cannot
   be a single distributed transaction; an external storage failure needs a
   recovery strategy for production.
5. **Upload failure orphan risk:** if MinIO upload succeeds and Library DB
   creation subsequently fails, an object can remain without a Library row.
6. **Worker deployment/concurrency:** no Compose worker, queue, locking,
   graceful shutdown, retry scheduler, or metrics.
7. **JWT trust architecture:** shared HS256 secret is only an MVP. Move to
   asymmetric verification or introspection before production.
8. **No upload quotas or content validation:** size/type limits and malware
   scanning are absent.
9. **No LLM resilience/cost controls:** no retries, backoff, caching, or token
   accounting.
10. **`object_proxy()` remains unused:** it points at an object-proxy endpoint
    that Library does not implement; its TODO must remain until that API exists.

## Before committing

```powershell
# Run in the edited service directory
python -m compileall app
git diff --check
git status --short
```

Commit only files relevant to the task. Keep separate logical changes in
separate commits. Never use destructive Git commands against a dirty tree.
