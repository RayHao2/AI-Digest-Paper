FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy dependency files first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into a project-local venv
RUN uv sync --frozen

# Copy source code
COPY src ./src
COPY README.md ./

# Create output directory
RUN mkdir -p /app/outputs

# Expose API port
EXPOSE 8000

# Run the FastAPI app
CMD [".venv/bin/python", "-m", "uvicorn", "paper_digest.api.app:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]