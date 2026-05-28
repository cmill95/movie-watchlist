FROM python:3.14-slim

# Install uv from the official distroless image
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

WORKDIR /code

# Copy everything into the image
COPY . .

# Install dependencies
RUN uv sync --frozen --no-dev

# Add the venv's bin directory to PATH
ENV PATH="/code/.venv/bin:$PATH"

# Run the app
CMD ["fastapi", "run", "app/main.py", "--host", "0.0.0.0", "--port", "8000"]
