#!/bin/bash

echo "Fixing Android SDK license..."
sudo mkdir -p /usr/lib/android-sdk/licenses
echo "24333f8a63b6825ea9c5514f83c2829b004d1fee" | sudo tee /usr/lib/android-sdk/licenses/android-sdk-license
echo "d56f5187479451eabf01fb78af6dfcb131a6481e" | sudo tee -a /usr/lib/android-sdk/licenses/android-sdk-license

echo ""
echo "License fixed! Now run:"
echo "cd client/flutter_app && flutter run"
