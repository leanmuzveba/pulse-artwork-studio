# Shared (services)

Code shared between the API and the worker.

| Folder | Purpose |
|--------|---------|
| `contracts/` | Job payload/result contracts and shared enums (e.g. job status lifecycle) |
| `logging/` | Structured-logging helpers with correlation ids |
| `utilities/` | Small cross-service helpers |

The job lifecycle both sides agree on:
`REQUESTED → QUEUED → PROCESSING → COMPLETED | FAILED`
