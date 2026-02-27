@echo off
REM ============================================================================
REM FastAPI Backend Server Startup Script
REM Binds to 0.0.0.0:8000 to allow connections from physical devices on the network
REM ============================================================================

echo.
echo ╔════════════════════════════════════════════════════════════════════════╗
echo ║  Morpheus FastAPI Backend - Starting on 0.0.0.0:8000                  ║
echo ║  Network Accessible: Yes (physical devices can connect)               ║
echo ║  Reload Mode: Enabled (auto-restart on code changes)                  ║
echo ╚════════════════════════════════════════════════════════════════════════╝
echo.

REM Activate virtual environment if it exists
if exist ".venv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
)

REM Start uvicorn server on 0.0.0.0:8000
REM Parameters:
REM   --host 0.0.0.0    : Bind to all network interfaces (required for physical devices)
REM   --port 8000       : Port number
REM   --reload          : Auto-reload on code changes
echo.
echo Starting Uvicorn server...
echo Command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

REM Keep window open if error occurs
pause
