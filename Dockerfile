FROM python:3.14-slim

# Install uv from the official distroless image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy everything into the image
COPY . .

# Install dependencies
RUN uv sync --frozen --no-dev

# Run the app
CMD ["/app/.venv/bin/fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
