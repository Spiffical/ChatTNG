#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to display help message
show_help() {
    echo "Development management script"
    echo
    echo "Usage:"
    echo "  $0 [command]"
    echo
    echo "Commands:"
    echo "  up        Start development environment"
    echo "  down      Stop development environment"
    echo "  logs      Show container logs"
    echo "  health    Run health checks"
    echo "  shell     Open a shell in the app container"
    echo "  help      Show this help message"
}

# Function to check if docker-compose is available
check_docker() {
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Error: docker-compose is not installed${NC}"
        exit 1
    fi
}

# Function to install health check dependencies
setup_health_check() {
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
    fi
    . venv/bin/activate
    pip install -r scripts/requirements.txt
}

# Main script
case "$1" in
    "up")
        check_docker
        docker-compose -f docker-compose.dev.yml up -d
        echo "🚀 Development environment is starting..."
        echo "📝 Use './dev.sh logs' to see the logs"
        echo "🏥 Use './dev.sh health' to run health checks"
        ;;
    "down")
        check_docker
        docker-compose -f docker-compose.dev.yml down
        echo "👋 Development environment stopped"
        ;;
    "logs")
        check_docker
        docker-compose -f docker-compose.dev.yml logs -f
        ;;
    "health")
        setup_health_check
        . venv/bin/activate
        DATABASE_URL="postgresql://postgres:postgres123@localhost:5432/chattng" \
        API_URL="http://localhost:8080" \
        python scripts/health_check.py
        ;;
    "shell")
        check_docker
        docker-compose -f docker-compose.dev.yml exec app /bin/bash
        ;;
    "help"|"")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac 