FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# onnxruntime (via rembg) needs libgomp at runtime; slim images don't ship it.
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

COPY worker ./worker

RUN useradd --create-home --uid 10001 appuser
USER appuser

CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
