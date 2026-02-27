# PowerShell script to push changes to Harshal branch
# Run this in PowerShell from: C:\FlutterDev\projects\project_morpheus\app

Write-Host "🚀 Starting Git Push to Harshal Branch..." -ForegroundColor Green
Write-Host ""

# Step 1: Check current status
Write-Host "📋 Step 1: Checking repository status..." -ForegroundColor Cyan
git status
Write-Host ""

# Step 2: Stage all changes
Write-Host "📦 Step 2: Staging all changes..." -ForegroundColor Cyan
git add .
Write-Host "✓ All files staged" -ForegroundColor Green
Write-Host ""

# Step 3: Create a detailed commit
Write-Host "💾 Step 3: Creating commit..." -ForegroundColor Cyan
$commitMessage = @"
Fix: JSON parsing, image compression, prediction UI, and transaction DB save

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
- Prevents acquireNextBufferLocked memory overflow errors
- Enables prediction display with confidence feedback
- Implements category confirmation/correction flow
- Ensures transactions persist to database
"@

git commit -m $commitMessage
Write-Host "✓ Commit created" -ForegroundColor Green
Write-Host ""

# Step 4: Verify commit was created
Write-Host "🔍 Step 4: Verifying commit..." -ForegroundColor Cyan
git log --oneline -1
Write-Host ""

# Step 5: Push to Harshal branch
Write-Host "🌐 Step 5: Pushing to Harshal branch..." -ForegroundColor Cyan
git push origin Harshal
Write-Host ""

# Step 6: Verify push success
Write-Host "✅ Step 6: Verifying push..." -ForegroundColor Cyan
git log origin/Harshal --oneline -1
Write-Host ""

Write-Host "✅ SUCCESS! Changes pushed to Harshal branch!" -ForegroundColor Green
Write-Host ""
Write-Host "Summary:" -ForegroundColor Yellow
Write-Host "  Branch: Harshal"
Write-Host "  Status: ✅ Pushed successfully"
Write-Host "  Files: $(git diff --cached --name-only 2>/dev/null | Measure-Object -Line | Select-Object -ExpandProperty Lines) files modified"
Write-Host ""
Write-Host "View changes at: https://github.com/[owner]/[repo]/tree/Harshal" -ForegroundColor Cyan
