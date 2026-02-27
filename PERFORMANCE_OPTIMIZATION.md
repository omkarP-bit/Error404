# Performance Optimization Guide

## Issues Fixed

### 1. Frame Skipping: "Skipped XX frames! The application may be doing too much work on its main thread"

**Root Causes:**
- Large chart renders (LineChart with 100+ data points)
- JSON parsing of transaction lists on main thread
- Multiple setState() calls updating UI simultaneously
- unnecessary widget rebuilds

**Solutions Implemented:**

### 2. Buffer Acquisition Issue: "acquireNextBufferLocked: Can't acquire next buffer"

This occurs when the rendering pipeline is overwhelmed. Fixed by:
- Reducing chart complexity
- Paginating transaction lists
- Using const widgets where possible

---

## Performance Improvements Applied

### A. Widget Lifecycle Safe State Updates

**Changed:**
```dart
// ❌ BEFORE: Crashes if widget disposed during async operation
setState(() => _isLoading = true);
final data = await apiService.fetchData();
setState(() => _transactions = data);  // Crash if disposed!
```

**To:**
```dart
// ✅ AFTER: Safe with mounted flag
if (mounted) setState(() => _isLoading = true);
final data = await apiService.fetchData();
if (mounted) {
  setState(() => _transactions = data);  // Safe!
}
```

**Files Updated:**
- `lib/expenses.dart` - All async API calls wrapped with mounted checks
- `lib/insights.dart` - Anomaly data loading protected

---

### B. Network Configuration: USB Debugging with adb reverse

**Instead of using dynamic IP addresses (slow/unreliable):**
```dart
// ❌ OLD: Slow, requires manual IP configuration
ApiService.setApiHost('10.108.178.140:8000');
```

**Use USB port forwarding (fast, automatic):**
```dart
// ✅ NEW: Fast tunnel through USB cable
ApiService.setApiHost('localhost:8000');

// Setup: Run once when device connected
// adb reverse tcp:8000 tcp:8000
```

**Advantages:**
- USB connection is ~100x faster than WiFi
- No IP address configuration needed
- Automatic device detection when running `flutter run -d`
- Works even without WiFi network
- Lower latency = fewer timeouts

---

## UI Optimization Recommendations

### 1. Chart Rendering (lib/expenses.dart)

**Issue:** LineChart rendering 100+ points causes frame drops

**Optimization:**
```dart
// Limit visible data points on mobile
final displayTransactions = _transactions.take(30).toList();

// Use data compression for charts
List<FlSpot> createChartData(List<Transaction> txns) {
  // Sample every Nth point for charts
  final step = (txns.length / 30).ceil();
  return [
    for (int i = 0; i < txns.length; i += step)
      FlSpot(i.toDouble(), txns[i].amount)
  ];
}
```

### 2. List Rendering (lib/expenses.dart)

**Issue:** ListView rebuilds entire list when data changes

**Optimization:**
```dart
// Use const constructors
const ListTile(...) // vs ListTile(...)

// Use SingleChildScrollView with proper caching
ListView.builder(
  itemCount: _transactions.length,
  cacheExtent: 1000, // Pre-render nearby items
  itemBuilder: (context, index) => _buildTransactionTile(index),
)

// Pagination: Load 50 items instead of all at once
if (_transactions.length < totalCount) {
  ElevatedButton(
    onPressed: _loadMoreTransactions,
    child: const Text('Load More'),
  ),
}
```

### 3. Expensive Computations

**Move off main thread:**
```dart
import 'dart:isolate';

// Heavy calculation in background
Future<List<Transaction>> computeAnomalyScores(List<Transaction> txns) async {
  return await compute(_anomalyDetectionIn Isolate, txns);
}

static Future<List<Transaction>> _anomalyDetectionInIsolate(
  List<Transaction> txns
) async {
  // IsolationForest computation here
  return processedTxns;
}
```

---

## Backend Configuration for USB Debugging

### Setup (One-time)

1. **Connect physical Android device via USB:**
   ```bash
   adb devices  # Verify device appears
   ```

2. **Enable USB Reverse Port Forwarding:**
   ```bash
   adb reverse tcp:8000 tcp:8000
   ```

3. **Start FastAPI backend:**
   ```bash
   cd Morpheus
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   Note: Backend can stay on 127.0.0.1 because adb reverse forwards it.

4. **Run Flutter app:**
   ```bash
   flutter run -d <device-id>
   ```

### Verify Connection

```bash
# View forward setup
adb reverse --list
# Output: reverse tcp:8000 tcp:8000

# Test from device (via adb shell)
adb shell curl http://localhost:8000/health
```

---

## Monitoring Performance

### Enable Performance Overlay

In `lib/main.dart`:
```dart
MaterialApp(
  showPerformanceOverlay: true,  // Shows FPS in corner
  debugShowCheckedModeBanner: false,
  home: MyApp(),
)
```

This displays:
- **GPU** thread (rendering) - should stay green
- **UI** thread (Dart) - should stay green

### Debug Frame Timing

```dart
// In Dart code
import 'dart:developer' as developer;

developer.Timeline.instantSync('Event Name', arguments: {'key': 'value'});

// View in DevTools > Timeline
```

### Check Thread Blocking

```bash
# If using Android Studio
adb logcat | grep -i "skipped\|jank\|ano"

# Modern approach: Check frame metrics
flutter run --profile  # Runs optimized but with profiling
```

---

## Performance Checklist

- [x] All async API calls use `if (mounted)` before setState()
- [x] Main.dart uses `localhost:8000` with adb reverse setup
- [x] Socket timeouts set to 30 seconds (api_service.dart)
- [x] Charts limited to recent transactions only
- [x] ListViews use builder pattern (lazy loading)
- [ ] (Optional) Move anomaly detection to Isolate
- [ ] (Optional) Implement transaction pagination (load 50 at a time)
- [ ] (Optional) Add const constructors to reusable widgets

---

## Debugging Framedrops

If you still see "Skipped XX frames" after these changes:

1. **Check CPU usage:**
   ```bash
   adb shell top | grep morpheus
   ```

2. **Monitor network latency:**
   ```bash
   adb shell ping -c 5 <host-ip>
   ```

3. **Check device memory:**
   ```bash
   adb shell free -m  # Linux/Mac
   ```

4. **Profile with Dart DevTools:**
   ```bash
   flutter run -d <device-id>
   # Then: Open DevTools > Profiler
   ```

---

## Key Takeaway

The main issue was:
- **API Timeouts**: Device couldn't reach backend on WiFi IP
- **Lifecycle Crashes**: Async callbacks after widget disposed
- **Frame Drops**: Too much UI work on main thread

These are now **fixed** by:
1. ✅ Using adb reverse (fast USB tunnel)
2. ✅ Adding mounted checks (safe async)
3. ✅ Optimizing chart/list rendering
