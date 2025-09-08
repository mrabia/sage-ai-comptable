# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for CrewAI, numpy, and python-magic
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    libstdc++6 \
    libgomp1 \
    pkg-config \
    gcc \
    g++ \
    libc6-dev \
    libffi-dev \
    libssl-dev \
    libmagic1 \
    libmagic-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Set environment variables for better numpy/CrewAI compatibility
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# Copy package files first for better caching
COPY frontend/package*.json ./frontend/
COPY backend/requirements.txt ./backend/

# Install backend dependencies first  
WORKDIR /app/backend
RUN pip install --upgrade pip setuptools wheel
RUN pip install numpy==1.24.3 --no-cache-dir
RUN pip install -r requirements.txt --no-cache-dir

# Install frontend dependencies
WORKDIR /app/frontend  
RUN npm install --legacy-peer-deps

# Copy application code (excluding files in .dockerignore)
WORKDIR /app
COPY . .

# Build frontend
WORKDIR /app/frontend
RUN npm run build

# Copy frontend build to backend static folder
RUN mkdir -p /app/backend/src/static && cp -r /app/frontend/dist/* /app/backend/src/static/

# Set final working directory
WORKDIR /app/backend

# Create uploads directory
RUN mkdir -p /app/backend/uploads
RUN mkdir -p /app/backend/database

# Create a non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (Railway will override with PORT env var)
EXPOSE 5000

# Set Python path to find modules
ENV PYTHONPATH=/app/backend

# Add Railway-specific environment
ENV RAILWAY_ENVIRONMENT=production

# Start command with full path and error handling
CMD ["python", "-u", "src/main.py"]