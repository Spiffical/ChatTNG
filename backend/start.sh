#!/bin/bash

# Enable error tracing and exit on error
set -ex

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

# Print system information
log "Starting application..."
log "Current user: $(id)"
log "Current directory: $(pwd)"
log "Directory contents:"
ls -la

log "Python version: $(python3 --version)"
log "Available memory:"
free -h
log "Running processes:"
ps aux

# Wait for database to be ready
log "Waiting for database to be ready..."
max_retries=${POSTGRES_MAX_RETRIES:-5}
retry_interval=${POSTGRES_RETRY_INTERVAL:-10}
retries=0

# Use synchronous URL from Railway directly
SYNC_DB_URL="${DATABASE_URL}"

while [ $retries -lt $max_retries ]; do
    if python3 -c "
import sys
import psycopg
try:
    conn = psycopg.connect(
        '${SYNC_DB_URL}',
        connect_timeout=${POSTGRES_CONNECT_TIMEOUT:-10},
        autocommit=True
    )
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f'Database connection failed: {str(e)}', file=sys.stderr)
    sys.exit(1)
"; then
        log "Database is ready"
        break
    else
        retries=$((retries + 1))
        if [ $retries -eq $max_retries ]; then
            log "Failed to connect to database after $max_retries attempts"
            exit 1
        fi
        log "Database not ready, waiting $retry_interval seconds... (attempt $retries/$max_retries)"
        sleep $retry_interval
    fi
done

# Run database migrations
log "Running database migrations..."
PYTHONPATH=/app/backend alembic upgrade head || {
    log "Migration failed - exiting..."
    exit 1
}

# Start uvicorn
log "Starting uvicorn..."
exec uvicorn main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8080} \
    --workers ${UVICORN_WORKERS:-1} \
    --log-level ${UVICORN_LOG_LEVEL:-INFO} \
    --timeout-keep-alive ${UVICORN_TIMEOUT:-75} 