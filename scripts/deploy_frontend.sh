#!/bin/bash

# Enable error handling
set -e

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

# Copy environment files
log "Copying environment files..."
./scripts/copy_env_files.sh

# Check if Vercel CLI is installed
if ! command -v vercel &> /dev/null; then
    log "Installing Vercel CLI..."
    npm install -g vercel
fi

# Navigate to frontend directory
cd frontend/chattng-web

# Install dependencies
log "Installing dependencies..."
npm install

# Check if user is logged in to Vercel
if ! vercel whoami &> /dev/null; then
    log "Please log in to Vercel..."
    vercel login
fi

# Make sure vercel-build.sh is executable
chmod +x vercel-build.sh

# Deploy to Vercel
log "Deploying to Vercel..."

# First deployment - configure project settings
if [ ! -f ".vercel/project.json" ]; then
    log "Initial deployment - configuring project..."
    vercel --yes
fi

# Production deployment - override build command
log "Deploying to production..."
vercel --prod --build-env CI=false

log "Frontend deployment completed!"

# Reminder for environment variables
log "Remember to set these environment variables in Vercel dashboard:"
echo "- VITE_API_URL (set to your Railway backend URL)"
echo "- VITE_WEBSOCKET_URL (set to your Railway backend WebSocket URL)"
echo "- VITE_CLOUDFRONT_DOMAIN (if applicable)" 