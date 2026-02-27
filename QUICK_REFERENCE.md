# Quick Commands Reference

## Essential Git Commands

### Check Status
```powershell
git status
```

### Stage All Changes
```powershell
git add .
```

### Create Commit
```powershell
git commit -m "Fix: JSON parsing, image compression, prediction UI, and transaction save"
```

### Push to Harshal
```powershell
git push origin Harshal
```

### ALL IN ONE
```powershell
git add . ; git commit -m "Fix: JSON parsing, image compression, prediction UI, and transaction save" ; git push origin Harshal
```

---

## Flutter Development Commands

### Get Latest Dependencies
```bash
flutter pub get
```

### Run on Device
```bash
flutter run
```

### Build APK
```bash
flutter build apk --split-per-abi
```

### Build iOS
```bash
flutter build ios
```

### Analyze Code
```bash
flutter analyze
```

### Format Code
```bash
dart format lib/
```

---

## Testing Commands

### Run Unit Tests
```bash
flutter test
```

### Run Specific Test File
```bash
flutter test test/widget_test.dart
```

### Run Tests with Coverage
```bash
flutter test --coverage
```

---

## View Changes

### See What's Different
```powershell
git diff
```

### See Staged Changes
```powershell
git diff --cached
```

### See Commit History
```powershell
git log --oneline -5
```

### See Branch Differences
```powershell
git diff main Harshal
```

---

## File Locations

| File | Purpose |
|------|---------|
| `lib/services/api_service.dart` | API service + safe type conversion |
| `lib/expenses.dart` | Main expense/transaction UI |
| `lib/utils/image_compression.dart` | Image optimization utility |
| `Morpheus/app/routers/categorization.py` | Backend API endpoints |
| `Morpheus/app/services/categorization_service.py` | Backend categorization logic |

---

## Import Statements

If needed, add these imports to files:

```dart
// In lib/expenses.dart:
import 'utils/image_compression.dart';

// In lib/services/api_service.dart:
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
```

---

## Pubspec Dependencies

Ensure pubspec.yaml has:
```yaml
dependencies:
  flutter:
    sdk: flutter
  cupertino_icons: ^1.0.8
  fl_chart: ^1.1.1
  go_router: ^17.1.0
  supabase_flutter: ^2.12.0
  http: ^1.1.0
  image_picker: ^1.0.0
  image: ^4.1.0  # ← NEW
```

---

## Key API Endpoints

### Categorize Transaction
```
POST /api/categorize
Parameters: raw_description, amount, merchant_name, txn_type, payment_mode, user_id, account_id
Response: { success, result: { category, subcategory, confidence_score, needs_confirmation } }
```

### Add Transaction to Database
```
POST /api/categorize/add-transaction
Parameters: raw_description, amount, category, subcategory, user_id, account_id, merchant_name, txn_type, payment_mode
Response: { success, txn_id, merchant_id, message }
```

### Process Receipt (OCR)
```
POST /api/categorize/ocr
Parameters: file (multipart), user_id, account_id
Response: { success, result: { ocr_merchant, ocr_amount, ocr_description } }
```

---

## Environment Variables

**Windows PowerShell**:
```powershell
$env:ANDROID_HOME = "C:\Android\sdk"
$env:FLUTTER_SDK = "C:\FlutterDev\flutter"
```

**Linux/Mac**:
```bash
export ANDROID_HOME="$HOME/Android/sdk"
export FLUTTER_SDK="$HOME/Flutter/flutter"
```

---

## Debug Tips

### Enable Verbose Logging
```dart
debugPrint('Message here');
```

### Check Device Logs
```bash
flutter logs
```

### Run with Debug Info
```bash
flutter run -v
```

### Disable Code Minification (for debugging)
```bash
flutter run --dart-define DEBUG=true
```

---

## Performance Checking

### Check Image File Size
```powershell
(Get-Item "path\to\image.jpg").Length / 1KB  # Size in KB
```

### Monitor Memory Usage
```
Android Studio → Profiler → Memory tab
```

---

## Common Issues & Solutions

### Issue: "Flutter command not found"
```powershell
# Add Flutter to PATH or use full path
C:\FlutterDev\flutter\bin\flutter run
```

### Issue: "Pubspec.lock out of sync"
```bash
flutter pub get
```

### Issue: "Gradle build fails"
```bash
flutter clean
flutter pub get
flutter build apk
```

### Issue: "Image decode fails"
```dart
// Graceful fallback already implemented
// Check debug logs for specific error
debugPrint('Image error: $e');
```

---

## File Modification Summary

**MODIFIED** (3 files):
1. `lib/services/api_service.dart` - Type conversion
2. `lib/expenses.dart` - UI & logic
3. `pubspec.yaml` - Dependencies

**CREATED** (1 file):
1. `lib/utils/image_compression.dart` - New utility

**DOCUMENTATION** (7 files):
1. `CHANGES.md` - Technical details
2. `FEATURE_GUIDE.md` - User guide
3. `IMPLEMENTATION_COMPLETE.md` - Summary
4. `README_FIXES.md` - Overview
5. `PUSH_TO_GIT.ps1` - Git script
6. `PUSH_TO_GIT.sh` - Git script
7. `VERIFICATION_CHECKLIST.md` - QA checklist

---

## Final Verification

```powershell
# Check everything is staged
git status

# Should show:
# modified:   lib/services/api_service.dart
# modified:   lib/expenses.dart
# modified:   pubspec.yaml
# new file:   lib/utils/image_compression.dart
# ... + documentation files

# Verify no errors
flutter analyze

# Check build (optional)
flutter build apk --dry-run
```

---

## Emergency Rollback (if needed)

```powershell
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1

# Undo staged changes
git restore --staged .

# Restore single file
git restore lib/expenses.dart
```

---

## Post-Deployment Verification

After pushing to GitHub:

```powershell
# Verify branch updated
git branch -v

# Check remote
git ls-remote origin

# View commit on branch
git log origin/Harshal --oneline -1
```

Expected output:
```
Fix: JSON parsing, image compression, prediction UI, and transaction save
```

---

## Support & References

**Documentation Files** (in project root):
- CHANGES.md - Full technical documentation
- FEATURE_GUIDE.md - Feature usage guide
- README_FIXES.md - Issue fixes overview
- VERIFICATION_CHECKLIST.md - QA checklist

**Code References**:
- lib/services/api_service.dart - Type conversions
- lib/expenses.dart - UI & prediction flow
- lib/utils/image_compression.dart - Image optimization

**External Resources**:
- Flutter Docs: https://flutter.dev/docs
- Dart Docs: https://dart.dev/guides
- JSON Parsing: https://flutter.dev/docs/development/data-and-backend/json

---

**Last Updated**: February 27, 2026
**Status**: Ready for Production ✅
