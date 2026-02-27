import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'dashboard.dart';
import 'expenses.dart';
import 'goals.dart';
import 'insights.dart';
import 'profile.dart';
import 'app_router.dart';
import 'services/api_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // ── Configure API Server Host ───────────────────────────────────────
  // Physical Android device (USB): Use adb reverse for localhost forwarding
  // Run: adb reverse tcp:8000 tcp:8000
  // Then use localhost:8000 here - device will tunnel through USB
  
  // For Android Emulator on same machine
  // ApiService.setApiHost('localhost:8000');
  
  // For physical Android device (USB with adb reverse) - DEFAULT
  ApiService.setApiHost('localhost:8000');
  
  // For Genymotion emulator
  // ApiService.setApiHost('10.0.3.2:8000');
  
  // For BlueStack emulator
  // ApiService.setApiHost('10.0.3.2:8000');
  
  debugPrint('✓ API Host: ${ApiService.getApiHost()}');
  debugPrint('✓ API Base URL: ${ApiService.baseUrl}');
  debugPrint('✓ On physical Android device, run: adb reverse tcp:8000 tcp:8000');
  // ────────────────────────────────────────────────────────────────────

  await Supabase.initialize(
    url: 'https://dgflbnjfuycdbitoxwgs.supabase.co',
    anonKey: 'sb_publishable_oseiv54g-oFdxh27mZvbRA_MA_fHFS8',
  );

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'Stocki Dashboard',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: DashboardScreen.accentGreen),
        useMaterial3: true,
        fontFamily: 'Roboto', // Default flutter font, fits the UI well
      ),
      routerConfig: appRouter,
    );
  }
}
