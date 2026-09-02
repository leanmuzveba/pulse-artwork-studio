# Pulse Worker (Celery)

Consumes Redis-backed jobs and runs CPU/GPU-intensive image and AI operations
off the request path, so the API and UI stay responsive.

## Run

```bash
docker compose up -d worker
docker compose logs -f worker
```

Standalone:

```bash
cd services/worker
pip install -e ".[dev]"
celery -A worker.celery_app worker --loglevel=info
```

## Verify the queue end-to-end

```python
from worker.tasks.system import ping
print(ping.delay().get(timeout=10))   # -> "pong"
```

## Job lifecycle

`REQUESTED → QUEUED → PROCESSING → COMPLETED | FAILED`

Tasks are late-acknowledged (`task_acks_late`) so a job re-runs if a worker dies
mid-flight, and prefetch is 1 for fair dispatch of long-running jobs.

## Adding a processor

Add a module under `worker/tasks/` (e.g. `enhancement.py`), register its task on
`celery_app`, and add the module to `include=[...]` in `worker/celery_app.py`.
