FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . /app/backend

# Create config directory and ensure it exists
RUN mkdir -p /app/config

# Copy config files from backend/config to /app/config
RUN cp -r /app/backend/config/* /app/config/

# Create startup script
COPY ./scripts/start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Create non-root user for security and set permissions
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Set environment variables
ENV PYTHONPATH=/app/backend
ENV PORT=8000

# Expose port
EXPOSE 8000

# Run the application with migrations
CMD ["/app/start.sh"] 