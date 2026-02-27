# Network Configuration Guide - Morpheus Backend & Flutter App

## Overview

This guide helps you set up the FastAPI backend and Flutter app to work with physical Android devices on the same network.

---

## Backend Configuration

### ✅ Option 1: Use the Startup Script (Recommended)

Simply run the provided script:

**Windows:**
```batch
Morpheus\run_server.bat
```

**Linux/Mac:**
```bash
bash Morpheus/run_server.sh
```

### 📋 Option 2: Manual Command

Run uvicorn directly with the correct host binding:

```bash
cd Morpheus
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Key Parameters:**
- `--host 0.0.0.0` — Binds to ALL network interfaces (required for physical devices)
- `--port 8000` — Uses port 8000
- `--reload` — Auto-restarts on code changes

### ❌ What NOT to do:

```bash
# ❌ WRONG - Only accessible from localhost
uvicorn app.main:app --reload

# ❌ WRONG - Still binds to localhost only
uvicorn app.main:app --reload --host 127.0.0.1
```

---

## Flutter App Configuration

### Finding Your Backend IP Address

First, find the IP address of the computer running the backend:

**Windows (Command Prompt):**
```cmd
ipconfig
```
Look for "IPv4 Address" under your network adapter (usually 192.168.x.x)

**Linux/Mac (Terminal):**
```bash
ifconfig
# or
hostname -I
```

### Configuring the Flutter App

In your main.dart or before initializing the API service, set the backend host:

```dart
import 'services/api_service.dart';

void main() {
  // Configure API host for physical devices
  // Replace 192.168.1.100 with your computer's actual IP address
  ApiService.setApiHost('192.168.1.100:8000');
  
  // Or keep default for emulator:
  // ApiService.setApiHost('localhost:8000');
  
  runApp(const MyApp());
}
```

### Example Configuration for Different Environments

```dart
void main() {
  // For emulator (development on same machine)
  ApiService.setApiHost('localhost:8000');
  
  // For physical device on same WiFi network
  // ApiService.setApiHost('192.168.1.100:8000');  // YOUR IP HERE
  
  // For physical device with Genymotion emulator
  // ApiService.setApiHost('10.0.3.2:8000');
  
  runApp(const MyApp());
}
```

---

## Testing Backend Connectivity

### From Flutter App (Windows/Linux/Mac)

```bash
# Test if the backend is accessible
curl http://YOUR_IP:8000/health

# Example:
curl http://192.168.1.100:8000/health
```

### From Android Device

```bash
# From adb shell on the device
curl http://192.168.1.100:8000/health
```

---

## Troubleshooting

### Physical Device Can't Connect

**Issue:** `Connection refused` or timeout

**Solutions:**
1. ✓ Ensure backend is running on `0.0.0.0:8000` (use startup script)
2. ✓ Check firewall on your computer (port 8000 should be open for local network)
3. ✓ Verify both devices are on the same WiFi network
4. ✓ Confirm you're using the correct IP address (run `ipconfig`)
5. ✓ Verify the IP in `ApiService.setApiHost()` matches your computer

### Localhost Works but Physical Device Doesn't

**Cause:** Backend is bound to `127.0.0.1` instead of `0.0.0.0`

**Fix:** Use the startup script or add `--host 0.0.0.0`:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Port 8000 Already in Use

**Error:** `Address already in use`

**Fix:** Kill existing process or use different port:
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8000
kill -9 <PID>
```

Then restart with `--port 8001` or similar.

---

## Configuration Checklist

- [ ] Backend runs with `--host 0.0.0.0 --port 8000`
- [ ] Found your computer's IP address (e.g., 192.168.1.100)
- [ ] Set `ApiService.setApiHost('YOUR_IP:8000')` in Flutter app
- [ ] Both devices are on the same WiFi network
- [ ] Firewall allows port 8000 (or temporarily disabled for testing)
- [ ] Backend is running and shows no errors
- [ ] Test connectivity with curl/browser: `http://YOUR_IP:8000/health`

---

## Default Configurations

### main.py (FastAPI)

The `if __name__ == "__main__"` block in `app/main.py` already has correct settings:

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
```

Run with: `python -m app.main`

### api_service.dart (Flutter)

The ApiService class now supports dynamic configuration:

```dart
// Default: localhost for emulator
static String _apiHost = 'localhost:8000';

// Change at runtime for physical devices
ApiService.setApiHost('192.168.1.100:8000');
```

---

## Additional Resources

- [Uvicorn Server Configuration](https://www.uvicorn.org/)
- [FastAPI Deployment Docs](https://fastapi.tiangolo.com/deployment/)
- [Flutter Network Communication](https://flutter.dev/docs/cookbook/networking/fetch-data)
