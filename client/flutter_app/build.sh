#!/bin/bash

# AR Budget Visualizer - Build Script
# This script builds the Flutter app for Android deployment

set -e

echo "🚀 Starting build process..."

# Navigate to project directory
cd "$(dirname "$0")"

echo "📦 Cleaning previous builds..."
flutter clean

echo "📥 Getting dependencies..."
flutter pub get

echo "🔍 Running code analysis..."
flutter analyze

echo "🏗️  Building APK (debug)..."
flutter build apk --debug

echo "✅ Build completed successfully!"
echo ""
echo "📱 APK location:"
echo "   build/app/outputs/flutter-apk/app-debug.apk"
echo ""
echo "To install on connected device:"
echo "   flutter install"
echo ""
echo "To build release APK:"
echo "   flutter build apk --release"
echo ""
echo "To build App Bundle for Play Store:"
echo "   flutter build appbundle --release"
