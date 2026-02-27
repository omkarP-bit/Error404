#!/bin/bash

# Fast Docker build script with optimizations
export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

echo "🚀 Building with optimized settings..."
echo "   - BuildKit enabled for parallel builds"
echo "   - Multi-stage caching enabled"
echo "   - .dockerignore files in place"

# Build with parallel processing
docker-compose up --build --parallel

echo "✅ Build complete!"