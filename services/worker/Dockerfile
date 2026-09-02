FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

COPY worker ./worker

RUN useradd --create-home --uid 10001 appuser
USER appuser

CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
