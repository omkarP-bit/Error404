import 'package:flutter/material.dart';

class EditProfileScreen extends StatefulWidget {
  final Map<String, dynamic> initialPreferences;

  const EditProfileScreen({Key? key, required this.initialPreferences}) : super(key: key);

  static const Color bgColor = Color(0xFF163339);
  static const Color cardBg = Color(0xFF1C3E45);
  static const Color accentGreen = Color(0xFF5DF22A);
  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Color(0xFF8BA5A8);

  @override
  State<EditProfileScreen> createState() => _EditProfileScreenState();
}

class _EditProfileScreenState extends State<EditProfileScreen> {
  late TextEditingController _incomeCtrl;
  late TextEditingController _expensesCtrl;
  late String _emergencyMonths;
  late String _goalHorizon;
  late double _riskSlider;
  late String _savingsHabit;
  late String _investmentKnowledge;
  late String _debtStatus;

  @override
  void initState() {
    super.initState();
    final prefs = widget.initialPreferences;
    _incomeCtrl = TextEditingController(text: prefs['income']);
    _expensesCtrl = TextEditingController(text: prefs['expenses']);
    _emergencyMonths = prefs['emergencyMonths'];
    _goalHorizon = prefs['goalHorizon'];
    _riskSlider = prefs['riskSlider'];
    _savingsHabit = prefs['savingsHabit'];
    _investmentKnowledge = prefs['investmentKnowledge'];
    _debtStatus = prefs['debtStatus'];
  }

  @override
  void dispose() {
    _incomeCtrl.dispose();
    _expensesCtrl.dispose();
    super.dispose();
  }

  void _savePreferences() {
    final updatedPrefs = {
      'income': _incomeCtrl.text,
      'expenses': _expensesCtrl.text,
      'emergencyMonths': _emergencyMonths,
      'goalHorizon': _goalHorizon,
      'riskSlider': _riskSlider,
      'savingsHabit': _savingsHabit,
      'investmentKnowledge': _investmentKnowledge,
      'debtStatus': _debtStatus,
    };
    Navigator.pop(context, updatedPrefs);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: EditProfileScreen.bgColor,
      appBar: AppBar(
        backgroundColor: EditProfileScreen.bgColor,
        elevation: 0,
        iconTheme: const IconThemeData(color: EditProfileScreen.textPrimary),
        title: const Text('Edit Profile', style: TextStyle(color: EditProfileScreen.textPrimary, fontWeight: FontWeight.bold)),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: EditProfileScreen.cardBg,
                borderRadius: BorderRadius.circular(18),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Financial Preferences', style: TextStyle(color: EditProfileScreen.textPrimary, fontSize: 18, fontWeight: FontWeight.bold)),
                  const SizedBox(height: 20),
                  _buildTextField(_incomeCtrl, "Monthly Income (₹)", keyboardType: TextInputType.number),
                  const SizedBox(height: 16),
                  _buildTextField(_expensesCtrl, "Fixed Monthly Expenses (₹)", keyboardType: TextInputType.number),
                  const SizedBox(height: 16),
                  
                  _buildDropdownField("Emergency Fund Months", _emergencyMonths, ["<1", "1–3", "3–6", "6+"], (val) => setState(() => _emergencyMonths = val!)),
                  const SizedBox(height: 16),
                  _buildDropdownField("Goal Horizon (Years)", _goalHorizon, ["<1", "1–3", "3–7", "7+"], (val) => setState(() => _goalHorizon = val!)),
                  
                  const SizedBox(height: 20),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text("Risk Comfort", style: TextStyle(color: EditProfileScreen.textSecondary, fontSize: 14)),
                      Text(_riskSlider.round().toString(), style: const TextStyle(color: EditProfileScreen.accentGreen, fontSize: 16, fontWeight: FontWeight.bold)),
                    ],
                  ),
                  Slider(
                    value: _riskSlider,
                    min: 0, max: 100, divisions: 100,
                    activeColor: EditProfileScreen.accentGreen,
                    inactiveColor: EditProfileScreen.bgColor,
                    onChanged: (val) => setState(() => _riskSlider = val),
                  ),
                  
                  _buildDropdownField("Savings Habit", _savingsHabit, ["Save what's left", "Pay myself first", "Erratic saver"], (val) => setState(() => _savingsHabit = val!)),
                  const SizedBox(height: 16),
                  _buildDropdownField("Investment Knowledge", _investmentKnowledge, ["None", "Some experience", "Advanced"], (val) => setState(() => _investmentKnowledge = val!)),
                  const SizedBox(height: 16),
                  _buildDropdownField("Debt Status", _debtStatus, ["No debt", "Only EMI/Mortgage", "Credit card dues", "Multiple loans"], (val) => setState(() => _debtStatus = val!)),
                  
                  const SizedBox(height: 24),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: EditProfileScreen.accentGreen,
                        foregroundColor: EditProfileScreen.bgColor,
                        padding: const EdgeInsets.symmetric(vertical: 14),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      onPressed: _savePreferences,
                      child: const Text('Save Preferences', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildDropdownField(String label, String value, List<String> items, ValueChanged<String?> onChanged) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(color: EditProfileScreen.textSecondary, fontSize: 13)),
        const SizedBox(height: 8),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          decoration: BoxDecoration(color: EditProfileScreen.bgColor, borderRadius: BorderRadius.circular(12)),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              isExpanded: true,
              dropdownColor: EditProfileScreen.cardBg,
              value: value,
              style: const TextStyle(color: EditProfileScreen.textPrimary, fontSize: 15),
              items: items.map((i) => DropdownMenuItem(value: i, child: Text(i))).toList(),
              onChanged: onChanged,
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildTextField(TextEditingController ctrl, String hint, {TextInputType? keyboardType}) {
    return TextField(
      controller: ctrl,
      keyboardType: keyboardType,
      style: const TextStyle(color: EditProfileScreen.textPrimary),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(color: EditProfileScreen.textSecondary),
        filled: true,
        fillColor: EditProfileScreen.bgColor,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
    );
  }
}
