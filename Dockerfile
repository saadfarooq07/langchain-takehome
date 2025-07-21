# Multi-stage build for efficient image
FROM oven/bun:1 as frontend-builder

WORKDIR /frontend
COPY frontend/package.json frontend/bun.lockb ./
RUN bun install --frozen-lockfile

COPY frontend/ ./
RUN bun run build

# Backend stage
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code
COPY . .

# Copy built frontend from previous stage
COPY --from=frontend-builder /frontend/build ./frontend/build

# Install the package in development mode
RUN pip install -e .

# Expose port
EXPOSE 8000

# Simple startup - no complex CLI
CMD ["python", "main.py"]