#!/bin/bash

# Docker Optimization Script
# Enables BuildKit and parallel builds for faster container creation

set -e

echo "🚀 Starting optimized Docker build..."

# Enable Docker BuildKit for faster builds
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

# Set build arguments for caching
BUILD_ARGS="--build-arg BUILDKIT_INLINE_CACHE=1"

echo "📦 Building containers with optimizations..."

# Build with parallel processing and caching
docker-compose build \
  --parallel \
  --compress \
  $BUILD_ARGS

echo "🔧 Optimizing images..."

# Prune unused build cache (keep recent layers)
docker builder prune -f --filter until=24h

echo "🏃 Starting services..."

# Start services with optimized settings
docker-compose up -d

echo "✅ Docker optimization complete!"
echo ""
echo "📊 Container Status:"
docker-compose ps

echo ""
echo "💾 Image Sizes:"
docker images | grep personal-finance

echo ""
echo "🔍 Health Checks:"
echo "Backend: http://localhost:3000/health"
echo "ML Service: http://localhost:8000/health"
echo "Database: localhost:5432"