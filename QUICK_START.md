# Quick Start: Backend + Android Device Setup

## 🎯 Summary of Changes

### Backend (FastAPI)
✅ **Binds to 0.0.0.0:8000** (all network interfaces)  
✅ **Works with --reload** (auto-restart on code changes)  
✅ **No hardcoded localhost bindings**  

### Flutter App
✅ **Dynamically configurable API host** (not hardcoded)  
✅ **Works with emulator and physical devices**  
✅ **Easy to switch environments**  

---

## 🚀 Quick Setup (5 Minutes)

### Step 1: Start the Backend Server

**On Windows:**
```batch
cd Morpheus
run_server.bat
```

**On Linux/Mac:**
```bash
cd Morpheus
bash run_server.sh
```

**Or manually:**
```bash
cd Morpheus
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete
```

### Step 2: Find Your Computer's IP Address

**Windows (Command Prompt):**
```cmd
ipconfig
```

Look for "IPv4 Address" - should be something like `192.168.1.100`

**Linux/Mac:**
```bash
hostname -I
```

### Step 3: Configure the Flutter App

Open `lib/main.dart` and add this at the start of `main()`:

```dart
void main() {
  // Configure API host for physical Android device
  // Replace with YOUR computer's actual IP address!
  ApiService.setApiHost('192.168.1.100:8000');
  
  // Or for emulator on same machine, use:
  // ApiService.setApiHost('localhost:8000');
  
  runApp(const MyApp());
}
```

### Step 4: Run the Flutter App

**On Android Device:**
```bash
flutter run -d <device_id>
```

**Or on emulator:**
```bash
flutter run -d emulator-5554
```

---

## ✅ Verification Checklist

- [ ] Backend running with output showing `http://0.0.0.0:8000`
- [ ] Found your computer's IP with `ipconfig` or `hostname -I`
- [ ] Updated `ApiService.setApiHost()` with correct IP
- [ ] Android device and computer on same WiFi network
- [ ] Flutter app connects and loads transactions ✓

---

## 🔧 API Host Configuration Examples

### Emulator on Same Machine
```dart
ApiService.setApiHost('localhost:8000');
```

### Physical Android on WiFi Network
```dart
ApiService.setApiHost('192.168.1.100:8000');  // YOUR IP HERE
```

### Genymotion Emulator
```dart
ApiService.setApiHost('10.0.3.2:8000');
```

### Using Configuration File
```dart
import 'config.dart';

void main() {
  ApiService.setApiHost(AppConfig.devHost);  // localhost:8000
  // ApiService.setApiHost('192.168.1.100:8000');  // Your WiFi IP
  runApp(const MyApp());
}
```

---

## 🐛 Troubleshooting

### Backend Won't Start
```
Error: Address already in use
```
Solution: Kill existing process on port 8000
```bash
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# Linux/Mac
lsof -i :8000
kill -9 <PID>
```

### App Can't Connect from Android
Check:
1. ✓ Backend is running on `0.0.0.0:8000` (not `127.0.0.1`)
2. ✓ Used correct IP in `ApiService.setApiHost('YOUR.IP:8000')`
3. ✓ Both devices on same WiFi network
4. ✓ Firewall allows port 8000

### Test Connection from Android
```bash
# From Android terminal or adb shell
curl http://192.168.1.100:8000/health
```

Should return:
```json
{"status":"ok","app":"Personal Finance Manager","version":"1.0.0"}
```

---

## 📁 Files Changed

### Backend
- ✅ `Morpheus/app/main.py` - Already has `host="0.0.0.0"`
- ✅ `Morpheus/run_server.bat` - New startup script for Windows
- ✅ `Morpheus/run_server.sh` - New startup script for Linux/Mac

### Flutter App
- ✅ `lib/services/api_service.dart` - Now has `setApiHost()` method
- ✅ `lib/config.dart` - Configuration examples
- ✅ `NETWORK_SETUP.md` - Detailed network guide

### Documentation
- ✅ `NETWORK_SETUP.md` - Complete setup guide
- ✅ `QUICK_START.md` - This file

---

## 📝 Summary

| Requirement | Status | How |
|---|---|---|
| Bind to 0.0.0.0:8000 | ✅ Done | Use `--host 0.0.0.0` or startup scripts |
| Works with --reload | ✅ Done | Uvicorn auto-restart enabled |
| No hardcoded localhost | ✅ Done | Use `ApiService.setApiHost()` |
| Physical device access | ✅ Done | Configure with computer's IP |
| Network accessible | ✅ Done | Verify with curl/browser |

**Your backend is now network-accessible to Android devices! 🎉**
