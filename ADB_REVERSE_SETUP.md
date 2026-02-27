# USB Debug Setup for Android Physical Device with adb reverse

## Overview

This guide explains how to run your Flutter app on a physical Android device connected via USB while keeping the FastAPI backend on your laptop.

**Problem:** Device can't access `10.x.x.x` IP addresses - they're laptop-specific.

**Solution:** Use `adb reverse` to tunnel `localhost:8000` through the USB cable to your laptop.

---

## Prerequisites

- Android device with USB debugging enabled
- USB cable connected to laptop
- Android SDK installed with `adb` command available

## Quick Setup (5 steps)

### 1. Enable USB Debugging on Device

**Android 11+:**
- Settings → About Phone → Tap "Build Number" 7 times
- Settings → Developer Options → USB Debugging → ON

**Android 10 and older:**
- Settings → Developer Options → USB Debugging → ON

### 2. Connect Device via USB

```bash
adb devices
# Should show:
# List of attached devices
# ABC123XYZ  device
```

If you see `unauthorized`, touch "Allow USB Debugging" prompt on device.

### 3. Set Up Port Forwarding (USB Reverse)

```bash
# Forward device's localhost:8000 to laptop's localhost:8000
adb reverse tcp:8000 tcp:8000

# Verify setup
adb reverse --list
# Output: reverse tcp:8000 tcp:8000
```

### 4. Start Backend on Laptop

```bash
cd Morpheus
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

✅ **Important:** Backend can stay on `127.0.0.1` (localhost only) because adb reverse handles forwarding.

### 5. Run Flutter App on Device

```bash
flutter run -d <device-id>

# Or without device-id (if only one device connected):
flutter run
```

That's it! ✅ The app now connects to your backend through the USB tunnel.

---

## Understanding adb reverse

### How It Works

```
Physical Device (USB)
     |
     | adb reverse tcp:8000 → tcp:8000
     |
Laptop (127.0.0.1:8000)
```

When your app makes a request to `http://localhost:8000`:
1. Request goes to device's port 8000
2. adb redirects it through USB cable to laptop
3. Laptop's port 8000 receives it (FastAPI backend)
4. Response comes back through USB cable

### Advantages over WiFi IP Method

| Aspect | WiFi IP | adb reverse |
|--------|---------|------------|
| Speed | ~100ms | ~5-10ms |
| Setup | Manual (find IP) | Automatic |
| Reliability | Network dependent | USB cable (guaranteed) |
| Works offline | ❌ Needs network | ✅ USB sufficient |
| Available without WiFi | ❌ No | ✅ Yes |

---

## Configuration in Flutter App

### main.dart (Already Updated)

```dart
Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // ✅ USB Device Setup (with adb reverse)
  ApiService.setApiHost('localhost:8000');
  
  debugPrint('✓ API Host: ${ApiService.getApiHost()}');
  debugPrint('✓ On USB: Run adb reverse tcp:8000 tcp:8000');
  
  // ... rest of initialization
}
```

### lib/services/api_service.dart

```dart
class ApiService {
  static String _apiHost = 'localhost:8000';
  
  static void setApiHost(String host) {
    _apiHost = host;
    debugPrint('✓ API Host configured to: http://$_apiHost/api');
  }
  
  static String get baseUrl => 'http://$_apiHost/api';
  
  // ... API methods
}
```

---

## Troubleshooting

### Issue: "adb devices" shows "unauthorized"

**Solution:**
1. Disconnect USB cable
2. On device: Settings → Developer Options → Revoke USB Debugging authorizations
3. Reconnect USB cable
4. Tap "Allow USB Debugging" on device prompt

```bash
adb devices
# Should now show: ABC123XYZ  device
```

### Issue: "Connection timeout" / "Failed to connect"

**Verify setup:**
```bash
# 1. Check port forwarding is active
adb reverse --list
# Should show: reverse tcp:8000 tcp:8000

# 2. Test backend is running on laptop
curl http://127.0.0.1:8000/health
# Should return: {"status":"ok",...}

# 3. Test from device via adb shell
adb shell curl http://localhost:8000/health
# Should also return same JSON

# 4. Restart port forwarding
adb reverse --remove tcp:8000
adb reverse tcp:8000 tcp:8000
```

### Issue: Gets new device ID each time

```bash
# View all connected devices with names
adb devices -l

# Use serial number explicitly
flutter run -d <serial-number>
```

### Issue: "Device not found" in Flutter

```bash
# Restart adb daemon
adb kill-server
adb start-server
adb devices

# Then try flutter run again
flutter run
```

### Issue: Backend running but app still times out

**Check these:**

1. **Backend actually running on 127.0.0.1:8000?**
   ```bash
   netstat -ano | findstr "8000"  # Windows
   # Should show: TCP 127.0.0.1:8000  LISTENING
   ```

2. **Port forwarding still active?**
   ```bash
   adb reverse --list
   # If empty, re-run: adb reverse tcp:8000 tcp:8000
   ```

3. **Firewall blocking port?**
   - Windows Defender Firewall may block port 8000
   - Settings → Windows Defender Firewall → Advanced → Inbound Rules
   - Add rule: Allow TCP 8000

---

## Workflow

### Daily Development

```bash
# 1. Connect device once at start of day
adb devices  # Verify connection

# 2. Start FastAPI backend
cd c:\FlutterDev\projects\project_morpheus\app\Morpheus
./run_server.bat  # Windows
# or
./run_server.sh  # Mac/Linux

# 3. In another terminal, run Flutter
flutter run -d <device-id>
```

### Switching Between Devices

```bash
# Run on physical device
flutter run -d <physical-device-id>

# Switch to emulator (without USB)
flutter run -d <emulator-id>
# WARNING: Emulator may need: adb reverse tcp:8000 tcp:10.0.2.2:8000
```

### Disconnecting Device

```bash
adb disconnect <device-id>
# OR just unplug USB cable
```

Note: adb reverse will be cleared when device disconnects.

---

## Advanced: Persistent Port Forwarding

If you want port forwarding to survive brief disconnections:

```bash
# Create shell script (save as setup_device.sh)
#!/bin/bash
while true; do
  adb devices | grep device > /dev/null
  if [ $? -eq 0 ]; then
    adb reverse tcp:8000 tcp:8000
    echo "✓ Port forwarding active"
  fi
  sleep 5
done
```

Run in background:
```bash
./setup_device.sh &
```

---

## Environmental Variables (Optional)

If you want to switch configs easily:

```dart
// lib/config.dart
const String API_HOST_DEVELOPMENT = 'localhost:8000';
const String API_HOST_STAGING = '192.168.1.100:8000';
const String API_HOST_PRODUCTION = 'api.example.com';

// In main.dart
ApiService.setApiHost(API_HOST_DEVELOPMENT);
```

---

## Summary

| Setting | Value |
|---------|-------|
| Backend Host | `127.0.0.1` (laptop localhost) |
| Backend Port | `8000` |
| Flutter App Host | `localhost:8000` |
| Connection | USB cable via `adb reverse` |
| Setup Time | 5 steps, ~2 minutes |

✅ **You're Ready!** Your physical Android device can now reach your FastAPI backend through a fast USB tunnel.
