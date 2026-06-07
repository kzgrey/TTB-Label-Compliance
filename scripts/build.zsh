#!/usr/bin/env zsh

set -e

echo "Starting build process..."

# Navigate to the project root directory
SCRIPT_DIR="${0:a:h}"
PROJECT_ROOT="${SCRIPT_DIR}/.."
cd "$PROJECT_ROOT"

# Install frontend dependencies locally for IDE support
echo "Installing frontend dependencies..."
cd src/frontend
npm install
cd ../..

# Install backend dependencies locally for IDE support
echo "Installing backend dependencies..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt || echo "Failed to install some python dependencies locally, continuing..."
fi

# Build Docker containers
echo "Building Docker containers..."
docker-compose build

echo "Build complete! You can now start the services using: docker-compose up"
