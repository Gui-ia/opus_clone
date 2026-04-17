FROM python:3.12-slim AS builder

RUN pip install uv

WORKDIR /app

COPY pyproject.toml ./
RUN uv sync --no-dev --no-install-project

COPY src/ src/

RUN uv sync --no-dev


FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY migrations/ migrations/
COPY scripts/ scripts/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONUNBUFFERED=1

EXPOSE 8080

CMD ["uvicorn", "opus_clone.api.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]
