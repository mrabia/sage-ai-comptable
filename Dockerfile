# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies required for CrewAI and numpy
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
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs

# Set environment variables for better numpy/CrewAI compatibility
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# Copy package files
COPY frontend/package*.json ./frontend/
COPY backend/requirements.txt ./backend/

# Install frontend dependencies
WORKDIR /app/frontend
RUN npm install --legacy-peer-deps

# Install backend dependencies
WORKDIR /app/backend

# Install numpy first with specific version for CrewAI compatibility
RUN pip install --upgrade pip setuptools wheel
RUN pip install numpy==1.24.3 --no-cache-dir

# Install other dependencies
RUN pip install -r requirements.txt --no-cache-dir

# Copy application code
WORKDIR /app
COPY . .

# Build frontend
WORKDIR /app/frontend
RUN npm run build

# Set final working directory
WORKDIR /app/backend

# Create uploads directory
RUN mkdir -p /app/backend/uploads
RUN mkdir -p /app/backend/database

# Create a non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8080

# Start command
CMD ["python", "src/main.py"]