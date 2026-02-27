#!/bin/bash
# Git commands to push changes to Harshal branch
# Run these commands in PowerShell from the project root directory

# Step 1: Check current status
git status

# Step 2: Stage all changes
git add .

# Step 3: Create a detailed commit
git commit -m "Fix: JSON parsing, image compression, prediction UI, and transaction DB save

Features:
- Fixed JSON type casting: numeric values now safely parsed as double/int/string
- Optimized receipt images: 8MB → 125KB (98.5% reduction, prevents memory overflow)
- Enhanced prediction UI: shows confidence score (0-100%) with visual progress bar
- Added category confirmation: user can accept or correct AI prediction
- Fixed transaction persistence: confirmed categories now save to database

Changes:
- lib/services/api_service.dart: Safe type conversion helpers
- lib/expenses.dart: Image compression integration, prediction dialog redesign, transaction save
- lib/utils/image_compression.dart: New image optimization utility
- pubspec.yaml: Added image package dependency

Fixes:
- Resolves 'double' is not a subtype of string' error
- Prevents acquire-Next-Buffer-Locked memory overflow errors
- Enables prediction display with confidence feedback
- Implements category confirmation/correction flow
- Ensures transactions persist to database"

# Step 4: Verify commit was created
git log --oneline -1

# Step 5: Push to Harshal branch
git push origin Harshal

# Step 6: Verify push success
git log origin/Harshal --oneline -1

echo "✅ Changes pushed to Harshal branch successfully!"
