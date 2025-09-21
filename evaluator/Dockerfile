FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy dependency files
COPY pyproject.toml ./

# Install Python dependencies using uv
RUN uv sync

# Copy application code
COPY src/ ./src/
COPY prompts/ ./prompts/

# Create logs directory
RUN mkdir -p logs

# Default command (will be overridden by docker-compose)
CMD ["uv", "run", "python", "-m", "src.evaluator"]