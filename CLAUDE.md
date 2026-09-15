# Structured Knowledge — repository guide

This document describes the code that is currently present in this repository. It
distinguishes implemented behavior from planned work; do not infer a public API or
a background process merely because the corresponding domain code exists.

## 1. Repository boundaries

The repository contains two independent FastAPI services:

| Directory | Ownership | Database | Host port |
| --- | --- | --- | --- |
| `backend/auth` | Users, password verification, JWT issue/refresh/validation | `auth_db` | `8001` |
| `backend/library` | Knowledge bases, sources, extracted content, chunks, compression | `library_db` | `8002` |

Each service has its own top-level Python package named `app`. They are not one
shared package. Therefore:

- Run Python, Alembic, and test commands from the directory of the target service.
- Never import `app.*` from the other service.
- Do not edit another service, its migrations, or its requirements for a task
  scoped to one service.
- Create a new Alembic revision for a schema change. Do not rewrite an applied
  initial migration.

The intended application layering is:

```text
FastAPI route -> DI factory/dependency -> domain service -> repository -> AsyncSession
```

Routes should not execute SQL. Repositories should not raise `HTTPException`.

## 2. Infrastructure and local development

The root [docker-compose.yml](docker-compose.yml) defines the following services:

| Compose service | Container | Ports | Network / dependency |
| --- | --- | --- | --- |
| `auth` | `knowledge_auth` | `8001 -> 8000` | `auth-network`, waits for `auth-postgres` |
| `library` | `knowledge_library` | `8002 -> 8000` | `library-network`, waits for `library-postgres` and MinIO |
| `auth-postgres` | `knowledge_auth_pg` | `5433 -> 5432` | PostgreSQL 16, `auth_db` |
| `library-postgres` | `knowledge_library_pg` | `5434 -> 5432` | PostgreSQL 16, `library_db` |
| `minio` | `knowledge_library_minio` | API `9000`, console `9001` | `library-network` |

```powershell
docker compose up --build
```

Source directories are bind-mounted into `/service`. The Dockerfiles start
`uvicorn app.main:app --host 0.0.0.0 --port 8000`; reload is not enabled.
The library image installs `ffmpeg`, required by video/media extraction.

### Environment files and secrets

Local `.env` files are intentionally Git-ignored. Never commit them, print
their contents, or place real API keys/tokens in this document. Use
`backend/library/.env.example` for the library service's variable names.

Library configuration is `app/core/config.py: Config`. It reads:

| Variable | Required | Notes |
| --- | --- | --- |
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | no | Compose supplies the DB host and port inside the containers. |
| `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`, `MINIO_BUCKET` | no | Inside Compose, endpoint must be `http://minio:9000`. |
| `OPENAI_API_KEY` | **yes** | `Config` raises `RuntimeError` during import when missing. |
| `COMPRESSION_MODEL` | no | Defaults to `gpt-5-mini`. |

Because `settings = Config()` is created at module import time, every library
command that imports `app.core.config` needs `OPENAI_API_KEY`, including the
current extraction smoke script. This is intentional current behavior, not a
lazy validation step.

Auth configuration is `backend/auth/app/core/config.py: Config`. Its
`SECRET_KEY` is required in practice to issue/validate JWTs. Auth defaults are
for local database connectivity only.

### Common commands

```powershell
# From backend/auth or backend/library, as appropriate
python -m compileall app
alembic upgrade head

# From repository root, after Compose is running
Invoke-RestMethod http://localhost:8001/health
Invoke-RestMethod http://localhost:8002/health
```

## 3. Auth service

`backend/auth/app/main.py` mounts `app.api.users.api_v1_router`. There is no
router prefix, so the available paths are:

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/health` | Returns `{"status": "OK"}`. |
| `POST` | `/register` | Creates a user; returns `UserPostCreateSchema`; status 201. |
| `POST` | `/login` | Validates credentials; returns access and refresh JWTs. |
| `POST` | `/refresh` | Validates a refresh token; returns a new pair. |
| `GET` | `/users` | Lists users. |
| `GET` | `/users/{user_id}` | Returns one user or a service-level 404. |
| `GET` | `/me` | Requires an access Bearer token; returns `UserPayload`. |

Key implementation locations:

- `app/api/users.py` — HTTP routes.
- `app/use_cases/users.py` — FastAPI dependencies and singleton password/token
  providers.
- `app/services/{register,login,refresh,users}.py` — domain flows.
- `app/repositories/users.py` — asynchronous persistence.
- `app/core/security/{password,token,deps}.py` — password/JWT helpers and
  current-user dependency.

The `users` table has a UUID primary key, unique `username`, password hash,
`is_active`, `is_staff`, and `created_at`. Access tokens last 15 minutes;
refresh tokens last 30 days. Refresh tokens are not persisted or revoked.

## 4. Library service overview

`backend/library/app/main.py` currently exposes **only** `GET /health`.
There are no Library HTTP routes, auth integration, background jobs, queue
consumers, or poll-worker. Domain services can be invoked by application code or
manual scripts, but nothing automatically schedules them.

Important directories:

```text
backend/library/
├── app/
│   ├── agents/compression.py
│   ├── abstractions/{knowledge,library,library_chunk,extraction}.py
│   ├── core/config.py
│   ├── db/{base,session}.py
│   ├── models/{knowledge,library,library_chunk}.py
│   ├── repositories/
│   │   ├── {knowledge,library,library_chunk}.py
│   │   └── extractors/{chunker,dispatcher,docs,media,pdf,webpage,youtube}.py
│   ├── services/{knowledge,library,extraction,compression,errors}.py
│   ├── storage/{document_storage,object_proxy}.py
│   └── use_cases/{extraction,compression}.py
├── scripts/{smoke_extraction,smoke_compression,smoke_compression_service}.py
└── tests/fixtures/smoke.pdf
```

### Data model

```text
Knowledge (1) -> Library (N) -> LibraryChunk (N)
```

| Table / model | Relevant fields |
| --- | --- |
| `knowledge` / `Knowledge` | UUID `id`, owner `user_id`, title, optional description, timestamps. |
| `library` / `Library` | UUID `id`, `knowledge_id`, source type, original reference, optional title, status, error, raw text, compressed text, ordering, timestamps. |
| `library_chunk` / `LibraryChunk` | UUID `id`, `library_id`, zero-based `order`, text. |

Enums from `app/schemas/enums.py`:

```text
SourceType:     file | url
LibraryStatus:  pending | extracting | extracted | compressing |
                compressed | quiz_ready | failed
```

The current useful pipeline states are:

```text
pending -> extracting -> extracted -> compressing -> compressed
                         \-> failed       \-> failed
```

There are no ORM relationships and the foreign keys do not use `ON DELETE
CASCADE`.

### Repositories and ownership

- `KnowledgeRepository` creates, reads, lists, updates, and deletes Knowledge.
- `LibraryRepository` creates, gets, lists by knowledge, updates status/content/
  title, and has `complete_compression()`.
- `LibraryChunkRepository.list_by_library(library_id)` already returns chunks
  ordered by `LibraryChunk.order ASC`.
- Write methods commit and refresh their entity.
- `complete_compression(library, compressed_content)` sets
  `compressed_content`, clears `error_message`, sets `compressed`, and does
  one commit. Use it rather than separate content/status writes when completing
  compression.

`KnowledgeService.get_owned_or_raise(knowledge_id, user_id)` is the ownership
gate for library operations. Any future HTTP API must take the user identity from
trusted auth context, not from a request body.

## 5. Extraction pipeline

### Construction

`app/use_cases/extraction.py` provides:

```python
dispatcher = build_extraction_dispatcher(settings)
service = build_extraction_service(session, settings)
```

The dispatcher is built with `DocumentStorage`, `PdfExtractor`,
`DocxExtractor`, one shared `MediaExtractor`, `WebpageExtractor`, and
`YoutubeExtractor(media_extractor=...)`.

`MediaExtractor` constructs its Faster-Whisper model immediately. Do not build
the extraction service per web request unless that startup cost is acceptable.

### Lifecycle and persistence

`ExtractionService.run(library)`:

1. Sets `library.status` to `extracting` and commits.
2. Runs `ExtractionDispatcher.extract(library)`.
3. On an exception, writes `failed` and `error_message=str(exception)`, then
   returns without re-raising.
4. Fills an empty library title from `ExtractedContent.title`.
5. For text at most `CHUNK_THRESHOLD_CHARS = 4000`, writes
   `Library.text_content`.
6. For longer text, deletes existing chunks, splits text, and writes replacement
   `LibraryChunk` rows.
7. Sets status to `extracted`.

The extraction storage threshold is a database-persistence rule. It must not be
reused as an LLM context-size decision without an explicit product decision.

### Dispatcher behavior

For `SourceType.file`, the dispatcher:

1. Uses the extension of `Library.original_ref`.
2. Fetches the object from MinIO.
3. Writes a temporary local file.
4. Calls the matching extractor.
5. Removes the temporary file in `finally`.

Supported extension mapping:

| Extensions | Extractor key |
| --- | --- |
| `pdf` | `pdf` |
| `docx` | `docx` |
| `mp3`, `wav`, `m4a` | `audio` |
| `mp4`, `mov`, `mkv` | `video` |

For URLs, a regular expression selects `youtube` for YouTube URLs and
`webpage` otherwise.

Extractor details:

- `PdfExtractor` uses `pypdf`; PDFs with too little text per page raise
  `EmptyTextLayerError`.
- `DocxExtractor` reads non-empty paragraphs via `python-docx`.
- `WebpageExtractor` fetches with `httpx` and extracts readable content with
  `trafilatura`.
- `MediaExtractor` invokes system `ffmpeg` for video audio-track extraction
  and transcribes with Faster-Whisper.
- `YoutubeExtractor` tries VTT subtitles from `yt-dlp` first; it parses VTT
  through `webvtt-py` and falls back to audio/STT if captions are unavailable or
  cannot be parsed.

`DocumentStorage` uses aioboto3 and does not create the bucket itself. The
calling environment must provide the bucket.

## 6. Compression pipeline

Compression has no DB work in `CompressionAgent`; DB state belongs exclusively
to `CompressionService`.

### CompressionAgent

Location: `app/agents/compression.py`.

```python
class CompressionAgent:
    def __init__(self, settings: Config, model: str | None = None) -> None: ...
    async def compress(self, text: str) -> str: ...
```

The agent uses the official async OpenAI client, `AsyncOpenAI`. It has no retry,
backoff, cache, token counter, or provider abstraction. SDK failures flow to its
caller unchanged.

Its behavior:

1. Empty or whitespace-only text raises `ValueError` without an API call.
2. Text shorter than `COMPRESSION_MAP_REDUCE_THRESHOLD_CHARS = 4000` receives
   one map-style compression request.
3. Longer text is split by
   `TextChunker(max_chunk_words=COMPRESSION_CHUNK_MAX_WORDS)`, currently 800
   words per chunk.
4. Map calls happen **sequentially**.
5. One separate reduce request merges the partial summaries into a connected
   outline.

The agent's character threshold and word-based chunk size are intentionally
separate from extraction's database storage threshold. They serve LLM request
budgeting, not `LibraryChunk` persistence.

### CompressionService

Location: `app/services/compression.py`.

```python
class CompressionService:
    def __init__(self, session: AsyncSession, agent: CompressionAgent) -> None: ...
    async def run(self, library: Library) -> None: ...
```

Behavior:

1. It rejects a library whose current status is not `extracted`.
2. It sets `compressing` and commits.
3. It uses nonblank `Library.text_content`; otherwise it obtains chunks from
   `LibraryChunkRepository.list_by_library()` and joins their already ordered
   text.
4. It calls `agent.compress(full_text)` once. Map-reduce is entirely an agent
   concern.
5. On success, `LibraryRepository.complete_compression()` atomically persists
   content and `compressed` status in one commit.
6. On an error after compression starts, it records `failed` and
   `error_message=str(error)`, then returns without re-raising.

Build it through:

```python
from app.use_cases.compression import build_compression_service

service = build_compression_service(session, settings)
```

The factory creates a fresh `CompressionAgent` and `CompressionService` on
every call. It does not cache either object.

## 7. Manual smoke scripts

These scripts are manual checks, not CI tests.

### PDF extraction

`scripts/smoke_extraction.py` creates a Knowledge and Library, uploads
`tests/fixtures/smoke.pdf` to MinIO, runs extraction, and prints status, raw
text, chunk count, and failure message.

```powershell
docker compose exec -T `
  -e OPENAI_API_KEY=$env:OPENAI_API_KEY `
  -e MINIO_ENDPOINT=http://minio:9000 `
  -e MINIO_ACCESS_KEY=$env:MINIO_ACCESS_KEY `
  -e MINIO_SECRET_KEY=$env:MINIO_SECRET_KEY `
  library python scripts/smoke_extraction.py
```

### Agent-only compression

`scripts/smoke_compression.py` does not use Docker, MinIO, or a database. It
calls the OpenAI API once for a short text and performs map-reduce for a generated
long text. It prints source/result character counts, output text, and map chunk
count.

```powershell
Set-Location backend/library
$env:OPENAI_API_KEY = "<your key>"
python scripts/smoke_compression.py
```

Install the service requirements first if the current local environment does not
already contain them.

### DB-backed CompressionService

`scripts/smoke_compression_service.py` creates a short extracted Library row,
constructs the service via `build_compression_service(session, settings)`, runs
it, and prints factory type, agent type, status before/after, and either the
compressed content or the persisted error.

```powershell
docker compose exec -T `
  -e OPENAI_API_KEY=$env:OPENAI_API_KEY `
  library python scripts/smoke_compression_service.py
```

No poll-worker currently invokes either smoke script or automatically advances an
`extracted` row to `compressing`.

## 8. Known limitations and follow-up work

The following are known, not silently solved:

1. **No Library HTTP API or auth integration.** Library has only health. A future
   API needs routing, DI, domain-error-to-HTTP mapping, and trusted user identity.
2. **No worker.** There is no polling loop, queue, locking strategy, or automatic
   scheduling for `pending` extraction or `extracted` compression.
3. **No cascade-delete policy.** Child rows/objects need an explicit deletion
   strategy before exposing destructive operations.
4. **Web SSRF risk.** `WebpageExtractor` accepts user-controlled URLs without
   private-address policy, redirect validation, or response-size limits.
5. **No OCR.** Scanned/image-only PDFs fail text-layer validation.
6. **Object proxy mismatch.** `object_proxy()` produces a document URL for
   which this service has no HTTP endpoint.
7. **No LLM retry/cost controls.** Compression has no retry/backoff, caching,
   token accounting, or provider abstraction.
8. **Media initialization cost.** Constructing `MediaExtractor` loads a Whisper
   model immediately.

## 9. Working-tree and safety rules

- Preserve unrelated dirty changes. Do not discard user work.
- Do not use `git reset --hard` or destructive checkout commands unless the user
  explicitly asks.
- Commit only files belonging to the requested change.
- Do not commit `.env`, virtual environments, `__pycache__`, generated output,
  API keys, passwords, JWTs, or password hashes.
