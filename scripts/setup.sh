#!/bin/bash

# Setup script for Stock Sentiment Analysis Bot

set -e

echo "================================================"
echo "Stock Sentiment Analysis Bot - Setup"
echo "================================================"
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "⚠️  IMPORTANT: Edit .env and add your Finnhub API key!"
    echo "   Get free API key at: https://finnhub.io/"
    echo ""
    read -p "Press Enter to continue or Ctrl+C to exit and edit .env first..."
else
    echo "✓ .env file exists"
fi

echo ""
echo "Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "❌ Docker not found. Please install Docker Desktop first."
    exit 1
fi
echo "✓ Docker is installed"

echo ""
echo "Checking Docker Compose..."
if ! docker compose version &> /dev/null; then
    echo "❌ Docker Compose not found. Please install Docker Desktop with Compose support."
    exit 1
fi
echo "✓ Docker Compose is installed"

echo ""
echo "================================================"
echo "Starting services..."
echo "================================================"
echo ""
echo "This will:"
echo "  1. Pull Docker images (MySQL, Ollama)"
echo "  2. Download Mixtral 8x7B model (~26GB)"
echo "  3. Initialize MySQL database"
echo "  4. Start the API server"
echo ""
echo "⏱️  Initial setup may take 15-30 minutes depending on your connection."
echo "   (Most of the time is downloading the Mixtral model)"
echo ""

# Build and start services
docker compose up -d --build

echo ""
echo "Services starting... waiting for initialization..."
echo ""

# Wait for services to be healthy
echo "Waiting for MySQL to be ready..."
for i in {1..30}; do
    if docker compose exec -T mysql mysqladmin ping -h localhost --silent 2>/dev/null; then
        echo "✓ MySQL is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ MySQL failed to start. Check logs: docker compose logs mysql"
        exit 1
    fi
    sleep 2
done

echo "Waiting for Ollama to be ready..."
for i in {1..60}; do
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo "✓ Ollama is ready"
        break
    fi
    if [ $i -eq 60 ]; then
        echo "❌ Ollama failed to start. Check logs: docker compose logs ollama"
        exit 1
    fi
    sleep 2
done

echo "Waiting for API server to be ready..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✓ API server is ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "❌ API server failed to start. Check logs: docker compose logs sentiment-api"
        exit 1
    fi
    sleep 2
done

echo ""
echo "================================================"
echo "✓ Setup Complete!"
echo "================================================"
echo ""
echo "Services are running:"
echo "  • API Server: http://localhost:8000"
echo "  • API Docs:   http://localhost:8000/docs"
echo "  • MySQL:      localhost:3306"
echo "  • Ollama:     http://localhost:11434"
echo ""
echo "Quick test:"
echo "  curl http://localhost:8000/health"
echo ""
echo "Analyze your first stock:"
echo "  curl -X POST http://localhost:8000/api/analyze/AAPL | jq"
echo ""
echo "View logs:"
echo "  docker compose logs -f"
echo ""
echo "Stop services:"
echo "  docker compose down"
echo ""
