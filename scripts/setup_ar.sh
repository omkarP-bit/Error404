#!/bin/bash

echo "Setting up AR Features for Personal Finance Platform"
echo "===================================================="

cd "$(dirname "$0")/../client/flutter_app"

echo ""
echo "1. Installing Flutter dependencies..."
flutter pub get

echo ""
echo "2. Checking Android configuration..."
MANIFEST_FILE="android/app/src/main/AndroidManifest.xml"

if [ -f "$MANIFEST_FILE" ]; then
    if ! grep -q "android.hardware.camera.ar" "$MANIFEST_FILE"; then
        echo "⚠️  WARNING: AR permissions not found in AndroidManifest.xml"
        echo "Please add the following to $MANIFEST_FILE:"
        echo ""
        echo "<uses-permission android:name=\"android.permission.CAMERA\" />"
        echo "<uses-feature android:name=\"android.hardware.camera.ar\" android:required=\"true\" />"
        echo "<uses-feature android:glEsVersion=\"0x00020000\" android:required=\"true\" />"
        echo ""
        echo "And inside <application> tag:"
        echo "<meta-data android:name=\"com.google.ar.core\" android:value=\"required\" />"
    else
        echo "✓ AR permissions found"
    fi
else
    echo "⚠️  AndroidManifest.xml not found"
fi

echo ""
echo "3. Checking build.gradle configuration..."
BUILD_GRADLE="android/app/build.gradle"

if [ -f "$BUILD_GRADLE" ]; then
    MIN_SDK=$(grep "minSdkVersion" "$BUILD_GRADLE" | grep -o '[0-9]*' | head -1)
    if [ "$MIN_SDK" -lt 24 ]; then
        echo "⚠️  WARNING: minSdkVersion is $MIN_SDK, AR requires 24+"
        echo "Please update minSdkVersion to 24 in $BUILD_GRADLE"
    else
        echo "✓ minSdkVersion is compatible ($MIN_SDK)"
    fi
else
    echo "⚠️  build.gradle not found"
fi

echo ""
echo "4. Checking iOS configuration..."
INFO_PLIST="ios/Runner/Info.plist"

if [ -f "$INFO_PLIST" ]; then
    if ! grep -q "NSCameraUsageDescription" "$INFO_PLIST"; then
        echo "⚠️  WARNING: Camera permission not found in Info.plist"
        echo "Please add camera usage description to $INFO_PLIST"
    else
        echo "✓ Camera permissions found"
    fi
else
    echo "⚠️  Info.plist not found"
fi

echo ""
echo "===================================================="
echo "Setup Summary:"
echo "✓ Dependencies installed"
echo ""
echo "AR Features Available:"
echo "  - AR Budget Visualizer"
echo "  - AR Spending Tracker"
echo "  - AR Receipt Scanner"
echo ""
echo "Next Steps:"
echo "1. Review and apply Android/iOS configuration changes above"
echo "2. Run 'flutter clean && flutter pub get'"
echo "3. Test on a physical device (AR doesn't work on emulators)"
echo ""
echo "Access AR features from the Dashboard -> AR Finance View card"
echo "===================================================="
