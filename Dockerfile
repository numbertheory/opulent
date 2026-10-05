# Use official Astral uv image with Python 3.13
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Install curl for container health checks
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*

# Install dependencies using cache mount
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copy application source code
COPY src/ ./src/
COPY README.md ./

# Install project package
RUN uv sync --frozen --no-dev

# Expose web service port
EXPOSE 8000

# Container healthcheck
HEALTHCHECK --interval=10s --timeout=5s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Run the web application using uvicorn
CMD ["uvicorn", "opulent.main:app", "--host", "0.0.0.0", "--port", "8000"]
