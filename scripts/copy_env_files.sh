#!/bin/bash

# Enable error handling
set -e

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

# Store the root directory
ROOT_DIR=$(pwd)

# Check if env/production directory exists
if [ ! -d "$ROOT_DIR/env/production" ]; then
    log "Error: env/production directory not found"
    exit 1
fi

# Copy frontend environment file
log "Copying frontend environment file..."
cp "$ROOT_DIR/env/production/.env.frontend" "$ROOT_DIR/frontend/chattng-web/.env.production"
log "Frontend environment file copied successfully"

# Copy backend environment file
log "Copying backend environment file..."
cp "$ROOT_DIR/env/production/.env.backend" "$ROOT_DIR/backend/.env"
log "Backend environment file copied successfully"

# Copy AWS environment file if needed
if [ -f "$ROOT_DIR/env/production/.env.aws" ]; then
    log "Copying AWS environment file..."
    cp "$ROOT_DIR/env/production/.env.aws" "$ROOT_DIR/aws/.env"
    log "AWS environment file copied successfully"
fi

log "All environment files copied successfully!"
log "Remember to deploy your applications to apply these changes." 