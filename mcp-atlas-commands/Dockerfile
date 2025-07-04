# Multi-stage build for optimized startup
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies for PyTorch, FAISS, and other ML libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libc6-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml setup.py ./
COPY src/ ./src/

# Upgrade pip and install the package with all dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -e . --timeout 300

# Pre-download ML models to cache them
RUN python -c "from sentence_transformers import SentenceTransformer; import torch; print('Pre-downloading models...'); model = SentenceTransformer('all-MiniLM-L6-v2'); print('Models cached successfully')"

# Runtime stage
FROM python:3.11-slim as runtime

# Install minimal runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy installed packages and cached models from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /root/.cache /root/.cache
COPY --from=builder /app /app

# Create non-root user
RUN useradd -m -u 1000 atlas && \
    chown -R atlas:atlas /app && \
    chown -R atlas:atlas /root/.cache
USER atlas

# Set environment variables for fast startup
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONOPTIMIZE=1
ENV ATLAS_STARTUP_MODE=fast
ENV ATLAS_LAZY_LOADING=true

# Expose the default MCP port (if needed)
EXPOSE 8765

# Health check for fast startup mode
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Run the MCP server
CMD ["python", "-m", "atlas_commands.server"]