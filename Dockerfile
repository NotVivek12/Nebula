# Stage 1: Build stage
FROM python:3.13-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.13-slim AS runner

# Create a non-root user
RUN groupadd -g 1000 nebula && \
    useradd -u 1000 -g nebula -m -s /bin/bash nebula

WORKDIR /workspace

# Install runtime dependencies (e.g., libpq for PostgreSQL connectivity)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed python dependencies from builder to non-root user home
COPY --from=builder --chown=nebula:nebula /root/.local /home/nebula/.local
ENV PATH=/home/nebula/.local/bin:$PATH

# Copy app code with correct ownership
COPY --chown=nebula:nebula app/ ./app/
COPY --chown=nebula:nebula alembic/ ./alembic/
COPY --chown=nebula:nebula alembic.ini .
COPY --chown=nebula:nebula pyproject.toml .

# Environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/workspace

EXPOSE 8000

# Switch to non-root user
USER nebula

# Run uvicorn server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
