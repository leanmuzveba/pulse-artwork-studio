# Pulse Artwork Studio AI

**Create · Enhance · Print Smarter.**

An AI-powered artwork-preparation platform for DTF (Direct-to-Film) printing and
garment decorators, by Pulse Machinery. It turns the low-resolution, poorly
cropped, non-transparent artwork print shops receive into production-ready output
through one workflow:

> **Upload → Analyze → Improve → Prepare → Preview → Export**

## Architecture

Flutter Web (client) → FastAPI (`/api/v1`) → Redis + Celery (async) → S3-compatible
object storage; PostgreSQL holds structured metadata only. Expensive image/AI work
runs in workers so the UI never blocks.

```
Flutter → HTTPS/API → FastAPI → job queue → AI/image worker → object storage → job status → Flutter
```

## Monorepo layout

```
apps/web/            Flutter Web client (dashboard, editor, API comms)
services/api/        FastAPI service — auth, projects, artworks, processing, exports
services/worker/     Celery workers — image & AI processing
services/shared/     Contracts/logging/utilities shared by api + worker
packages/            Shared libs (design_system, image_models, api_contracts)
infrastructure/      Docker, nginx, postgres, redis, object storage, monitoring
docs/                Documentation (source specs in intial_docs/)
.github/workflows/   CI: flutter-ci, backend-ci, worker-ci, deploy
docker-compose.yml   Local dev stack
```

## Quick start (local)

Requires Docker. Then:

```bash
cp .env.example .env
docker compose up -d --build      # or: ./scripts/dev-up.sh
```

| Service | URL |
|---------|-----|
| API docs (OpenAPI) | http://localhost:8000/docs |
| API health | http://localhost:8000/health |
| MinIO console | http://localhost:9001 |

The Flutter client runs separately:

```bash
cd apps/web && flutter pub get && flutter run -d chrome
```

Verify the async queue end-to-end:

```python
from worker.tasks.system import ping
ping.delay().get(timeout=10)   # -> "pong"
```

## Development

- **Backend:** `cd services/api && pip install -e ".[dev]" && pytest && ruff check .`
- **Worker:** `cd services/worker && pip install -e ".[dev]" && pytest`
- **Web:** `cd apps/web && flutter analyze && flutter test`

Branch model: `main` (production) ← `develop` (integration) ← `feature/*`,
`fix/*`, `release/*`, `hotfix/*`. See [CONTRIBUTING.md](CONTRIBUTING.md).

## Non-negotiable rules

1. Original artwork is **immutable** — every operation writes a new derived asset.
2. AI/image jobs are **asynchronous** — never block a request.
3. Provider **API keys stay server-side** — never shipped to the Flutter client.
4. Secrets live in the environment; never commit `.env` or keys.
5. Large binary assets live in **object storage**, not Git.
6. API contracts are **versioned**; DB changes ship with **migrations**.
7. Every feature gets **tests**; PRs require review and green CI.

## Status

**Phase 1 — Foundation** (in progress). Repo, service scaffolds, async pipeline,
CI, and local stack are up. Next: PostgreSQL models & migrations, email/password
auth, and the signed-URL upload flow. See `docs/` for the roadmap.

## License

Proprietary — © Pulse Machinery. See [LICENSE](LICENSE).
