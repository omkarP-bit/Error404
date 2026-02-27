import 'package:shared_preferences/shared_preferences.dart';

class LocalUserSettings {
  static const String _surplusKey = 'monthly_surplus';

  Future<double> getMonthlySurplus() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getDouble(_surplusKey) ?? 0.0;
  }

  Future<void> setMonthlySurplus(double value) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_surplusKey, value);
  }
}
