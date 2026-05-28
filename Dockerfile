# ---- Stage 1: builder ----
FROM python:3.14-slim AS builder

# uv only needs to exist here, in the builder
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

WORKDIR /code
COPY . .
RUN uv sync --frozen --no-dev

# ---- Stage 2: runtime ----
FROM python:3.14-slim AS runtime

WORKDIR /code

# Bring over only the .venv and the Python code in app from Builder stage
COPY --from=builder /code/.venv /code/.venv
COPY --from=builder /code/app /code/app

ENV PATH="/code/.venv/bin:$PATH"
CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
