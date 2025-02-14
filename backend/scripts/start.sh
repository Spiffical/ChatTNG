#!/bin/bash

# Wait for database to be ready
echo "Waiting for database..."
while ! nc -z db 5432; do
  sleep 1
done
echo "Database is ready!"

# Run migrations
echo "Running database migrations..."
cd /app/backend
alembic upgrade head

# Start the application
echo "Starting application..."
exec uvicorn api.main:app --host 0.0.0.0 --port 8000 