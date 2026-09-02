# Pulse API (FastAPI)

The authenticated REST API. Coordinates auth, projects, artworks, upload
orchestration, processing jobs, exports and entitlements. Public routes live
under `/api/v1`.

## Run

With the full stack (recommended):

```bash
docker compose up -d api
# http://localhost:8000/docs
```

Standalone (needs Python 3.12):

```bash
cd services/api
python -m venv .venv && source .venv/Scripts/activate   # Windows Git Bash
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

## Test

```bash
cd services/api
pytest
ruff check .
```

## Layout

```
app/
  main.py              app factory, middleware, exception handlers
  core/                config, logging, errors, request-context middleware
  api/v1/router.py     aggregates the versioned route surface
  api/v1/routes/       one module per service boundary (health implemented;
                       auth/projects/artworks/processing/exports/... stubbed)
  db/                  Base + mixins, enums, async session, models/
  schemas/             response envelopes
migrations/            Alembic (env.py + versions/)
tests/                 smoke tests
```

## Database & migrations

Async SQLAlchemy 2.0 over PostgreSQL (asyncpg). Models live in `app/db/models/`:
`users`, `projects`, `artworks`, `processing_jobs`, `exports`, `entitlements`,
`audit_logs`. Originals are immutable — a processing operation writes a new
derived `artworks` row pointing at its parent.

```bash
# Apply migrations (run from services/api, with DATABASE_URL set)
alembic upgrade head

# Autogenerate a new migration after changing models
alembic revision --autogenerate -m "describe change"

# Preview SQL without a database
alembic upgrade head --sql
```

In Docker, the one-shot `migrate` service runs `alembic upgrade head` before the
API starts. Readiness (`GET /api/v1/health/ready`) reports DB connectivity;
liveness (`GET /api/v1/health`) does not touch the DB.

## Conventions

- Every response uses the success/error envelope in `app/schemas/common.py`.
- Errors carry a stable machine-readable `code` (`app/core/errors.py`).
- Every request gets an `X-Request-ID`, echoed in the response and in logs.
- Secrets come from the environment only — never hard-coded, never sent to the client.
