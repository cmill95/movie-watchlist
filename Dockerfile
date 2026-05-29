# ---- Stage 1: builder ----
FROM python:3.14-slim AS builder

# uv only needs to exist here, in the builder
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

# Force uv to use the base image's system Python instead of downloading and managing its own
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /code
COPY . .
RUN uv sync --frozen --no-dev

# ---- Stage 2: runtime ----
FROM python:3.14-slim AS runtime

# Create an unprivileged user with a fixed, predictable UID
RUN useradd -m -u 1000 app

WORKDIR /code

# Give user permissions for necessary files in /code
COPY --from=builder --chown=app:app /code/.venv /code/.venv
COPY --from=builder --chown=app:app /code/app /code/app

ENV PATH="/code/.venv/bin:$PATH"

# Give the app a writable directory for the SQLite DB
ENV MOVIES_DB_PATH=/data/movies.db
RUN mkdir -p /data && chown app:app /data

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health').read()" || exit 1

CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
