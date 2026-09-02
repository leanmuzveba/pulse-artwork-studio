FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install dependencies first (better layer caching).
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .

# App source.
COPY app ./app

EXPOSE 8000

# Non-root runtime user.
RUN useradd --create-home --uid 10001 appuser
USER appuser

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
