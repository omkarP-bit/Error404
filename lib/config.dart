/// Configuration module for API connection settings
/// Allows easy switching between development, emulator, and production environments

abstract class AppConfig {
  /// API Host configuration
  /// 
  /// Default: 'localhost:8000' (for emulator on same machine)
  /// For physical device: Set to your computer's IP (e.g., '192.168.1.100:8000')
  /// 
  /// Example:
  /// ```dart
  /// // In main.dart
  /// void main() {
  ///   // For emulator development
  ///   ApiService.setApiHost(AppConfig.devHost);
  ///   
  ///   // For physical Android device on same WiFi
  ///   // ApiService.setApiHost('192.168.1.100:8000');
  ///   
  ///   runApp(const MyApp());
  /// }
  /// ```
  
  // Development (emulator/same machine)
  static const String devHost = 'localhost:8000';
  
  // Production (physical device via network)
  // ⚠️ CHANGE THIS TO YOUR COMPUTER'S IP ADDRESS
  static const String productionHost = 'YOUR_COMPUTER_IP:8000';
  
  // Example hosts (uncomment and use appropriately)
  // static const String exampleWiFi = '192.168.1.100:8000';      // WiFi LAN
  // static const String exampleGenymotion = '10.0.3.2:8000';     // Genymotion emulator
  // static const String exampleBluestack = '10.0.3.2:8000';      // BlueStack emulator
}

