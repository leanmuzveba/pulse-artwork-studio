# Contributing

## Branch model

| Branch | Role |
|--------|------|
| `main` | Production-ready releases (protected) |
| `develop` | Integration branch |
| `feature/*` | Individual features |
| `fix/*` | Bug fixes |
| `release/*` | Release preparation |
| `hotfix/*` | Urgent production fixes |

Branch off `develop` for features; open a PR back into `develop`. Releases merge
`develop → main`.

## Workflow

1. Create a branch: `git switch -c feature/short-name`.
2. Make the change **with tests**.
3. Run checks locally (see per-service READMEs).
4. Open a PR using the template. CI must pass; at least one review is required.

## Ground rules

- Never commit secrets, API keys, or `.env`.
- Never commit large binary assets — they belong in object storage.
- API contracts are versioned; database changes include a committed migration.
- AI/image work must be asynchronous (Celery), never inline in a request.
- Original artwork is immutable — create new derived assets, never overwrite.

## Commit messages

Short imperative subject (e.g. `add signed-url upload flow`), context in the body
if needed. Reference issues with `Closes #123`.

## Code style

- Python: `ruff` (lint + import order), type hints, `pytest`.
- Dart/Flutter: `flutter analyze`, `flutter_lints`, feature-first structure.
