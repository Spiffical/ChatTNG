#!/bin/bash

# Enable error handling
set -e

# Function to log with timestamp
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  -p, --project PROJECT_ID  Link to existing Railway project"
    echo "  -h, --help               Show this help message"
    echo ""
    echo "Example:"
    echo "  $0 --project your-project-id"
}

# Parse command line arguments
PROJECT_ID=""
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--project)
            PROJECT_ID="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Store the root directory
ROOT_DIR=$(pwd)

# Copy environment files
log "Copying environment files..."
./scripts/copy_env_files.sh

# Check if Railway CLI is installed
if ! command -v railway &> /dev/null; then
    log "Installing Railway CLI..."
    npm install -g @railway/cli
fi

# Check if user is logged in to Railway
if ! railway whoami &> /dev/null; then
    log "Please log in to Railway..."
    railway login
fi

# Check if railway.toml exists
if [ ! -f "railway.toml" ]; then
    log "Error: railway.toml not found in root directory"
    exit 1
fi

# Link to Railway project if not already linked
if [ ! -f ".railway/config.json" ]; then
    log "Linking to Railway project..."
    railway link
fi

# Deploy to Railway using configuration from railway.toml
log "Deploying to Railway using Docker configuration..."
log "Current directory structure:"
tree -L 3 backend/
log "Contents of backend/config:"
ls -la backend/config/
log "Verifying Docker build locally first..."
docker build -f docker/backend/Dockerfile.prod . --no-cache
log "Local Docker build successful, proceeding with Railway deployment..."

# Set Railway environment variables
export RAILWAY_DOCKERFILE_PATH=docker/backend/Dockerfile.prod
export RAILWAY_BUILD_CONTEXT=.

log "Using Dockerfile at: $RAILWAY_DOCKERFILE_PATH"
log "Using build context: $RAILWAY_BUILD_CONTEXT"
railway up --detach

# Wait for deployment to complete and get the URL
log "Waiting for deployment to complete..."
sleep 15  # Give it more time to start
DEPLOY_URL=$(railway domain)
log "Backend deployed successfully!"
log "Deployment URL: $DEPLOY_URL"

# Show deployment logs first
log "Checking deployment logs for any issues..."
railway logs

# Verify the deployment with retries
log "Verifying deployment..."
MAX_RETRIES=5
RETRY_COUNT=0
HEALTH_CHECK_URL="https://$DEPLOY_URL/ping"

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    log "Checking ping endpoint (attempt $((RETRY_COUNT + 1))/$MAX_RETRIES)..."
    RESPONSE=$(curl -s "$HEALTH_CHECK_URL")
    log "Response from ping check: $RESPONSE"
    
    if [ -n "$RESPONSE" ] && echo "$RESPONSE" | grep -q "ok"; then
        log "Ping check passed!"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            log "Ping check failed, waiting 10 seconds before retry..."
            
            # Try health endpoint as fallback
            HEALTH_RESPONSE=$(curl -s "https://$DEPLOY_URL/health")
            log "Health endpoint response: $HEALTH_RESPONSE"
            
            sleep 10
        else
            log "Warning: Health check did not return healthy status after $MAX_RETRIES attempts."
            log "Please check the following:"
            echo "1. Visit https://$DEPLOY_URL/health in your browser"
            echo "2. Check Railway logs in the dashboard"
            echo "3. Verify environment variables are set correctly"
            echo "4. Check if the database connection is working"
        fi
    fi
done

# Reminder for environment variables
log "Remember to verify these environment variables in Railway dashboard:"
echo "- DATABASE_URL (Railway will auto-configure this)"
echo "- REDIS_URL (if using Redis)"
echo "- AWS_ACCESS_KEY_ID (for S3 access)"
echo "- AWS_SECRET_ACCESS_KEY (for S3 access)"
echo "- OPENAI_API_KEY"
echo "- PINECONE_API_KEY"
echo "- JWT_SECRET"
echo "- CORS_ORIGINS (set to your Vercel frontend URL)"

# Print deployment URL again for convenience
log "Your backend is deployed at: https://$DEPLOY_URL"
log "You can check the health endpoint at: $HEALTH_CHECK_URL" 