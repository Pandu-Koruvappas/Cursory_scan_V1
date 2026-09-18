# --- BA Agent Pro: Backend-Only Image ---
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy backend requirements and install
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir --only-binary :all: --require-hashes --upgrade pip && \
    pip install --no-cache-dir --only-binary :all: --require-hashes -r ./backend/requirements.txt

# Copy backend code
COPY backend/ ./backend/

# Expose port
EXPOSE 8000

# Azure App Service optimization
ENV PORT=8000

# Create a non-root user for security
RUN useradd -m appuser
USER appuser

# Use gunicorn with uvicorn workers for production stability
CMD ["gunicorn", "backend.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120"]
