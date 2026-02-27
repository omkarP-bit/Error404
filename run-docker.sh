#!/bin/bash

echo "🚀 Starting Personal Finance Platform with AR Support..."

# Clean up any existing containers
docker-compose down --remove-orphans

# Build and start services
docker-compose up --build -d

# Wait for services to be healthy
echo "⏳ Waiting for services to start..."
sleep 10

# Check service health
echo "🔍 Checking service health..."
docker-compose ps

# Show logs for any failed services
for service in backend ml-service camera-service postgres; do
    if ! docker-compose ps $service | grep -q "Up"; then
        echo "❌ $service failed to start. Logs:"
        docker-compose logs $service
    else
        echo "✅ $service is running"
    fi
done

echo "🎯 Platform ready!"
echo "📱 Backend: http://localhost:3000"
echo "🤖 ML Service: http://localhost:8000"
echo "📷 Camera Service: http://localhost:8080"
echo "🗄️ Database: localhost:5432"