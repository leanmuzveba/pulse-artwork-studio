#!/usr/bin/env bash
# Bring up the local development stack.
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "No .env found — creating one from .env.example"
  cp .env.example .env
fi

docker compose up -d --build
echo
echo "Stack is starting. Useful endpoints:"
echo "  API docs      http://localhost:8000/docs"
echo "  API health    http://localhost:8000/health"
echo "  MinIO console http://localhost:9001"
echo
echo "Follow logs:  docker compose logs -f api worker"
