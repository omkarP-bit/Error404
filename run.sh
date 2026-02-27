#!/bin/bash

echo "🚀 Starting Personal Finance Platform..."

# Check if required tools are installed
command -v node >/dev/null 2>&1 || { echo "❌ Node.js not installed"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "❌ Python3 not installed"; exit 1; }
command -v flutter >/dev/null 2>&1 || { echo "❌ Flutter not installed"; exit 1; }

# Start ML Service
echo "🤖 Starting ML Service..."
cd ml
python3 src/api/main.py &
ML_PID=$!
cd ..
sleep 3

# Start Backend
echo "⚙️  Starting Backend API..."
cd backend
npm install --silent
npm start &
BACKEND_PID=$!
cd ..
sleep 5

# Start Flutter App
echo "📱 Starting Flutter App..."
cd client/flutter_app
flutter pub get
flutter run -d chrome &
FLUTTER_PID=$!
cd ../..

echo ""
echo "✅ All services started!"
echo ""
echo "📊 Backend API: http://localhost:3000"
echo "🤖 ML Service: http://localhost:8000"
echo "📱 Flutter App: Running in Chrome"
echo ""
echo "Press Ctrl+C to stop all services"

# Cleanup on exit
trap "echo ''; echo '🛑 Stopping services...'; kill $ML_PID $BACKEND_PID $FLUTTER_PID 2>/dev/null; exit" INT TERM

wait
