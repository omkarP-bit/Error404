class AppConfig {
  static const String apiBaseUrl = 'http://localhost:3000/api';
  static const String supabaseUrl = 'https://ugppmqetpqswhgdbmikw.supabase.co';
  static const String supabaseAnonKey = 'YOUR_NEW_ANON_KEY_HERE';
  
  static const int requestTimeout = 30000;
  static const String appVersion = '1.0.0';
}

class ApiEndpoints {
  static const String transactions = '/transactions';
  static const String budgets = '/budgets';
  static const String goals = '/goals';
  static const String alerts = '/alerts';
  static const String investments = '/investments';
}
