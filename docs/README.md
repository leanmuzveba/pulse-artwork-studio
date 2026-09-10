# Docs

Project documentation.

- **Source specifications** live in [`../intial_docs/`](../intial_docs/): the PRD
  v1.0, Technical Design v1.0, repo architecture, FDD, and use-case diagram.
- The **build roadmap** (phased plan for the MVP) is maintained as a shared
  artifact — see the project lead.

Planned structure as docs grow: `prd/`, `architecture/`, `api/`, `ux/`,
`security/`, `testing/`, `release/`.

### Status (as of 2026-09-10)

Phase 1 (Foundation) and most of Phases 2–3 (AI Engine, Creative Engine) are
done — auth, storage, the Celery job pipeline, enhance/upscale, background
removal, the AI Inspector, vector conversion, halftone, and embroidery
simulation are all shipped. Database Schema & API Contract are implemented
(SQLAlchemy models + Alembic migrations), so that's no longer the next spec.

Remaining MVP work (see the roadmap artifact for detail):
- Model-adapter abstraction for AI providers (architectural, do before adding
  more AI features)
- Editor canvas tools (crop / rotate / flip / resize)
- Dedicated print checks (clipping, fine lines, small text)
- White-underbase preview
- Gang sheet builder
