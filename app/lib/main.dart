import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'dashboard.dart';
import 'expenses.dart';
import 'goals.dart';
import 'insights.dart';
import 'profile.dart';
import 'app_router.dart';

// Provide a safe way to check desktop platforms without throwing UnsupportedError on Web
bool get _isDesktop {
  if (kIsWeb) return false;
  return defaultTargetPlatform == TargetPlatform.windows || 
         defaultTargetPlatform == TargetPlatform.linux || 
         defaultTargetPlatform == TargetPlatform.macOS;
}

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  if (_isDesktop) {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  }

  await Supabase.initialize(
    url: 'https://pqoowyipqypdbuijwnyt.supabase.co',
    anonKey: 'sb_publishable_ZoRhSYjSrXlBDmTQyU6YAQ_IJ6-JYZJ',
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
