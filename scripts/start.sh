#!/bin/bash

echo "🚀 Starting Personal Finance Platform..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ .env file not found. Please create one from .env.example"
    exit 1
fi

# Start Docker services
echo "📦 Starting Docker services..."
docker-compose up -d postgres

# Wait for PostgreSQL
echo "⏳ Waiting for PostgreSQL..."
sleep 5

# Run migrations
echo "🗄️  Running database migrations..."
docker exec -i $(docker-compose ps -q postgres) psql -U postgres -d personal_finance < supabase/migrations/001_initial_setup.sql

# Seed data (optional)
read -p "Do you want to seed test data? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🌱 Seeding test data..."
    docker exec -i $(docker-compose ps -q postgres) psql -U postgres -d personal_finance < supabase/seed/test_data.sql
fi

# Start ML service
echo "🤖 Starting ML service..."
cd ml
pip install -r requirements.txt > /dev/null 2>&1
python src/api/main.py &
ML_PID=$!
cd ..

# Start backend
echo "⚙️  Starting backend..."
cd backend
npm install > /dev/null 2>&1
npm start &
BACKEND_PID=$!
cd ..

echo ""
echo "✅ All services started!"
echo ""
echo "📊 Backend API: http://localhost:3000"
echo "🤖 ML Service: http://localhost:8000"
echo "🗄️  PostgreSQL: localhost:5432"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for Ctrl+C
trap "echo ''; echo '🛑 Stopping services...'; kill $ML_PID $BACKEND_PID; docker-compose down; exit" INT
wait
