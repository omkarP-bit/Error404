#!/bin/bash
# ============================================================================
# FastAPI Backend Server Startup Script
# Binds to 0.0.0.0:8000 to allow connections from physical devices on the network
# ============================================================================

echo ""
echo "╔════════════════════════════════════════════════════════════════════════╗"
echo "║  Morpheus FastAPI Backend - Starting on 0.0.0.0:8000                  ║"
echo "║  Network Accessible: Yes (physical devices can connect)               ║"
echo "║  Reload Mode: Enabled (auto-restart on code changes)                  ║"
echo "╚════════════════════════════════════════════════════════════════════════╝"
echo ""

# Activate virtual environment if it exists
if [ -f ".venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Start uvicorn server on 0.0.0.0:8000
# Parameters:
#   --host 0.0.0.0    : Bind to all network interfaces (required for physical devices)
#   --port 8000       : Port number
#   --reload          : Auto-reload on code changes
echo ""
echo "Starting Uvicorn server..."
echo "Command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
