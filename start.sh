#!/bin/bash

echo "======================================"
echo "Project Manager - Quick Start"
echo "======================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"
echo ""

# Create data directory
mkdir -p data
echo "✅ Created data directory for database"
echo ""

# Build and start containers
echo "🔨 Building and starting containers..."
docker-compose up -d

# Check if containers started successfully
if [ $? -eq 0 ]; then
    echo ""
    echo "======================================"
    echo "✅ Project Manager is running!"
    echo "======================================"
    echo ""
    echo "🌐 Open your browser and visit:"
    echo "   http://localhost:5000"
    echo ""
    echo "📝 Useful commands:"
    echo "   Stop:  docker-compose down"
    echo "   Logs:  docker-compose logs -f"
    echo "   Restart: docker-compose restart"
    echo ""
else
    echo ""
    echo "❌ Failed to start containers. Check the logs:"
    echo "   docker-compose logs"
fi
