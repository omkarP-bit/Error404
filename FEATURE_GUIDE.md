# Quick Reference Guide - New Features

## User Flow: Receipt Scanning → Categorization → Save

### Step 1: Scan Receipt 📸
```
User clicks "Scan Receipt" button
  ↓
Choose Camera or Gallery
  ↓
Image captured/selected
  ↓
Automatically resized/compressed (max 1024x1280, <500KB)
  ↓
Sent to backend for OCR
```

### Step 2: View Prediction with Confidence 🎯
```
Prediction dialog appears showing:
  • Confidence Score (0-100%)
  • Visual progress bar (green/orange)
  • Suggested Category
  • Subcategory (if available)
  • Transaction details preview
```

**Confidence Interpretation**:
- ✅ **Green (≥85%)** - High confidence, safe to save
- ⚠️ **Orange (<85%)** - Medium confidence, review recommended

### Step 3: Confirm or Correct Category ✏️
```
Two action buttons:

  "Correct Category" → Opens category picker
  "Add Transaction" → Saves to database
```

If correcting, user can select from:
- Food & Dining
- Transport
- Shopping
- Health & Medical
- Entertainment
- Bills & Utilities
- Education
- Investment
- Savings
- Other

### Step 4: Transaction Saved ✅
```
Success feedback:
  • Snackbar shows "✓ Transaction saved! #[ID]"
  • Form automatically clears
  • Parent list refreshes
  • Ready for next transaction
```

---

## Technical Details

### Image Compression
**File**: `lib/utils/image_compression.dart`

```dart
// Compress before upload
String optimizedPath = await ImageCompressionUtil.compressReceiptImage(imagePath);

// Check dimensions
var dims = await ImageCompressionUtil.getImageDimensions(imagePath);
print('${dims.width}x${dims.height}');
```

**Settings**:
- Max width: 1024 px
- Max height: 1280 px  
- JPEG quality: 75 (60 fallback)
- Max file size: 500 KB

### JSON Parsing
**Safe conversion for all numeric types**:
```dart
// Automatically handles:
// "amount": "123.45"    (String)
// "amount": 123.45      (Double)
// "amount": 123         (Int)
// "amount": null        (Null)

final amount = _toDouble(json['amount']) ?? 0.0;
```

### Confidence Score
**Display & Interpretation**:
```dart
final confidence = 0.87;  // From backend (0.0-1.0)
final percentage = (confidence * 100).toInt();  // → 87%

// Styling
if (confidence >= 0.85) {
  // Green color + "High confidence"
} else {
  // Orange color + "Medium confidence"
}
```

---

## Error Handling

### Image Compression Fails
```
Scenario: Image too corrupted to read
Result: Uses original image, continues with OCR
```

### OCR Processing Fails
```
Scenario: Receipt text unreadable
Result: Shows error, allows manual entry
```

### Prediction Too Uncertain
```
Scenario: Confidence < 0.85
Result: Shows orange warning, asks user to confirm
```

### Database Save Fails
```
Scenario: Network error or DB issue
Result: Shows red error snackbar with details
User can retry submission
```

---

## API Endpoints Used

### 1. Get Prediction
```
POST /api/categorize
Body: raw_description, amount, merchant_name, txn_type, payment_mode, user_id, account_id
Response: { success, result: { category, subcategory, confidence_score, needs_confirmation } }
```

### 2. Process Receipt Image
```
POST /api/categorize/ocr
Body: file (multipart), user_id, account_id
Response: { success, result: { ocr_merchant, ocr_amount, ocr_description } }
```

### 3. Save Transaction
```
POST /api/categorize/add-transaction
Body: raw_description, amount, category, subcategory, user_id, account_id, merchant_name, txn_type, payment_mode
Response: { success, txn_id, merchant_id, message }
```

---

## Debugging Tips

### Enable Verbose Logging
```dart
// Check image compression
debugPrint('Compressed: ${(compressedSize / 1024).toStringAsFixed(2)} KB');

// Check prediction
debugPrint('Confidence: ${(confidence * 100).toInt()}%');

// Check API response
debugPrint('Response: ${jsonResponse}');
```

### Monitor Image Processing
```
Original: 3456x4608, 8.4 MB
  ↓ (compress with resize)
Optimized: 1024x1280, 125 KB (98.5% reduction!)
```

### Verify Database Save
```
Check response.txnId != null
Check response.success == true
Monitor snackbar feedback
```

---

## Known Limitations

1. **Max Image Size**: 1024x1280 px
   - Larger receipts may lose fine detail
   - Solution: Crop before scanning

2. **OCR Accuracy**: Depends on receipt quality
   - Solution: Manually verify extracted values

3. **Category List**: Fixed 10 categories
   - Solution: Modify `_showCategoryPickerDialog()` to add custom

4. **Confidence Threshold**: 0.85
   - Backend setting in `CONFIDENCE_THRESHOLD`

---

## Future Enhancement Ideas

- [ ] Multi-image receipt support (split bills)
- [ ] Custom category creation
- [ ] Barcode scanning for products
- [ ] Receipt templates by merchant
- [ ] Offline categorization cache
- [ ] Receipt archival/search
- [ ] Expense trend predictions

---

**Support**: For issues or questions, check `CHANGES.md` for implementation details.
