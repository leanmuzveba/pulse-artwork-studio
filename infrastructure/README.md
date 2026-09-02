# Infrastructure

Deployment and operational configuration. Populated as environments are built.

| Folder | Purpose |
|--------|---------|
| `docker/` | Shared Docker assets and per-environment compose overrides |
| `nginx/` | Reverse proxy / TLS termination config |
| `postgres/` | DB init, tuning, backup scripts |
| `redis/` | Redis config for broker + cache |
| `object_storage/` | Bucket policies, lifecycle rules (auto-expire exports) |
| `monitoring/` | Metrics, logs, alerts (queue depth, job failures, API errors) |

Local development is driven by the root `docker-compose.yml`. Staging and
production use managed PostgreSQL, Redis and object storage with separate
buckets and secrets — production data is never shared with dev/test.
