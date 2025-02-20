#!/bin/bash

# Enable error tracing and exit on error
set -ex

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

# Start the application with more verbose logging
log "Starting application..."
log "Environment variables:"
env | grep -v "KEY\|SECRET\|PASSWORD"
log "Current directory: $(pwd)"
log "Python path: $PYTHONPATH"

# Debug Python environment
log "Python sys.path:"
python -c "import sys; print('\n'.join(sys.path))"
log "Available modules in backend:"
ls -la /app/backend

# Run database migrations first
cd /app/backend
log "Running database migrations..."
PYTHONPATH=/app/backend alembic upgrade head || {
    log "Migration failed - exiting..."
    exit 1
}

# Wait for database to be fully ready
log "Waiting for database to be fully ready..."
sleep 5

# Start uvicorn with proper module path
cd /app/backend
log "Starting uvicorn from $(pwd) with PYTHONPATH=$PYTHONPATH"
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port 8080 \
    --workers 1 \
    --log-level debug \
    --no-access-log \
    --timeout-keep-alive 75 