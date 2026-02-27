#!/bin/bash

echo "Installing ADB..."
sudo apt update
sudo apt install -y adb

echo ""
echo "Starting ADB server..."
adb start-server

echo ""
echo "Checking connected devices..."
adb devices

echo ""
echo "Now run: flutter devices"
