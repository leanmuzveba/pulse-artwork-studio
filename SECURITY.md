# Security Policy

## Reporting a vulnerability

Please report suspected vulnerabilities privately to the Pulse Machinery team
rather than opening a public issue. Include steps to reproduce and impact. We'll
acknowledge and keep you updated on remediation.

## Security requirements (enforced across the platform)

- **Transport:** TLS everywhere.
- **Auth:** secure password hashing, protected sessions / JWT, per-user & per-project authorization.
- **Uploads:** MIME/type verification, file-size limits, malware scanning where appropriate.
- **Storage:** private by default; signed, time-limited URLs for access. Users can never enumerate or reach another user's storage keys.
- **API:** input validation, rate limiting, secure CORS, CSRF protection where cookie-based auth is used.
- **Secrets:** environment-only; least privilege. **AI provider keys remain server-side and are never exposed to the Flutter client.**
- **Audit:** authentication events, entitlement changes, and administrative actions are logged.
- **Privacy:** customer artwork is private and is not used for analytics or model training without explicit consent.

## What never goes in the repo

Secrets, API keys, `.env` files, customer artwork, or any private binary assets.
Dependency and secret scanning run in CI.
