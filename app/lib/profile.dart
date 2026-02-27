import 'package:flutter/material.dart';
import 'edit_profile.dart';

class AccountItem {
  String id;
  String name;
  String type; // 'bank', 'credit_card', 'wallet'
  String maskedId;
  double balance;

  AccountItem({
    required this.id,
    required this.name,
    required this.type,
    required this.maskedId,
    required this.balance,
  });
}

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({Key? key}) : super(key: key);

  static const Color bgColor = Color(0xFF163339);
  static const Color cardBg = Color(0xFF1C3E45);
  static const Color accentGreen = Color(0xFF5DF22A);
  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Color(0xFF8BA5A8);

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  // --- Header State ---
  String _riskTag = "Balanced";
  int _stabilityScore = 72;

  // --- Accounts State ---
  final List<AccountItem> _accounts = [
    AccountItem(
      id: '1',
      name: 'HDFC Credit Card',
      type: 'credit_card',
      maskedId: '**** 4582',
      balance: 15240,
    ),
    AccountItem(
      id: '2',
      name: 'Cash on Hand',
      type: 'wallet',
      maskedId: 'Wallet',
      balance: 2400,
    ),
    AccountItem(
      id: '3',
      name: 'SBI Savings',
      type: 'bank',
      maskedId: '**** 8821',
      balance: 124000,
    ),
  ];

  // --- Preferences State (kept here to track insights globally) ---
  String _income = "60000";
  String _expenses = "35000";
  String _emergencyMonths = "1–3";
  String _goalHorizon = "1–3";
  double _riskSlider = 55.0;
  String _savingsHabit = "Save what's left";
  String _investmentKnowledge = "Some experience";
  String _debtStatus = "Credit card dues";

  // --- Computed Insights State ---
  double _disposableIncome = 25000;
  double _savingsRate = 41.67;



  // Helper formatting ₹
  String _formatCurrency(double amount) {
    String str = amount.round().toString();
    String result = '';
    int count = 0;
    for (int i = str.length - 1; i >= 0; i--) {
      result = str[i] + result;
      count++;
      if (count == 3 && i != 0) {
        result = ',' + result;
      } else if (count > 3 && (count - 3) % 2 == 0 && i != 0) {
        result = ',' + result;
      }
    }
    return '₹$result';
  }

  void _recalculateTargetStates() {
    setState(() {
      double income = double.tryParse(_income) ?? 0;
      double expenses = double.tryParse(_expenses) ?? 0;

      // Derived Insights
      _disposableIncome = income - expenses;
      if (income > 0) {
        _savingsRate = (_disposableIncome / income) * 100;
      } else {
        _savingsRate = 0;
      }

      // Risk Tag
      if (_riskSlider <= 33) {
        _riskTag = "Conservative";
      } else if (_riskSlider <= 66) {
        _riskTag = "Balanced";
      } else {
        _riskTag = "Aggressive";
      }

      // Stability Score
      int score = 50;
      if (_emergencyMonths == "3–6") {
        score += 10;
      } else if (_emergencyMonths == "6+") {
        score += 20;
      }

      if (_savingsRate >= 20) {
        score += 10;
      }

      if (_debtStatus == "Credit card dues" || _debtStatus == "Multiple loans") {
        score -= 10;
      }
      
      _stabilityScore = score.clamp(0, 100);
    });
  }

  void _showAccountSheet({AccountItem? account}) {
    final bool isEdit = account != null;
    final nameCtrl = TextEditingController(text: account?.name ?? '');
    final maskedIdCtrl = TextEditingController(text: account?.maskedId ?? '');
    final balanceCtrl = TextEditingController(text: account?.balance.toString() ?? '');
    String selectedType = account?.type ?? 'bank';

    showModalBottomSheet(
      context: context,
      backgroundColor: ProfileScreen.cardBg,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setSheetState) {
            return Padding(
              padding: EdgeInsets.only(
                bottom: MediaQuery.of(context).viewInsets.bottom,
                left: 20, right: 20, top: 24,
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    isEdit ? "Edit Account" : "Add New Account",
                    style: const TextStyle(color: ProfileScreen.textPrimary, fontSize: 20, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 20),
                  _buildTextField(nameCtrl, "Account Name", keyboardType: TextInputType.text),
                  const SizedBox(height: 16),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(horizontal: 16),
                    decoration: BoxDecoration(
                      color: ProfileScreen.bgColor,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: DropdownButtonHideUnderline(
                      child: DropdownButton<String>(
                        dropdownColor: ProfileScreen.cardBg,
                        value: selectedType,
                        style: const TextStyle(color: ProfileScreen.textPrimary, fontSize: 16),
                        items: const [
                          DropdownMenuItem(value: 'bank', child: Text('Bank Account')),
                          DropdownMenuItem(value: 'credit_card', child: Text('Credit Card')),
                          DropdownMenuItem(value: 'wallet', child: Text('Wallet')),
                        ],
                        onChanged: (val) {
                          if (val != null) setSheetState(() => selectedType = val);
                        },
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  _buildTextField(maskedIdCtrl, "Identifier (e.g. **** 1234)", keyboardType: TextInputType.text),
                  const SizedBox(height: 16),
                  _buildTextField(balanceCtrl, "Balance", keyboardType: TextInputType.number),
                  const SizedBox(height: 32),
                  SizedBox(
                    width: double.infinity,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: ProfileScreen.accentGreen,
                        foregroundColor: ProfileScreen.bgColor,
                        padding: const EdgeInsets.symmetric(vertical: 16),
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      onPressed: () {
                        final newAccount = AccountItem(
                          id: isEdit ? account.id : DateTime.now().millisecondsSinceEpoch.toString(),
                          name: nameCtrl.text,
                          type: selectedType,
                          maskedId: maskedIdCtrl.text,
                          balance: double.tryParse(balanceCtrl.text) ?? 0.0,
                        );

                        setState(() {
                          if (isEdit) {
                            final idx = _accounts.indexWhere((acc) => acc.id == account.id);
                            if (idx != -1) _accounts[idx] = newAccount;
                          } else {
                            _accounts.add(newAccount);
                          }
                        });
                        Navigator.pop(context);
                      },
                      child: const Text('Save Account', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                    ),
                  ),
                  const SizedBox(height: 24),
                ],
              ),
            );
          },
        );
      },
    );
  }

  void _deleteAccount(String id) {
    setState(() {
      _accounts.removeWhere((acc) => acc.id == id);
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: ProfileScreen.bgColor,
      body: SafeArea(
        child: SingleChildScrollView(
          child: Padding(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildHeaderCard(),
                const SizedBox(height: 24),
                _buildSectionTitle('Accounts', actionText: '+ Add New', onAction: () => _showAccountSheet()),
                const SizedBox(height: 12),
                ..._accounts.map((acc) => _buildAccountCard(acc)),
                const SizedBox(height: 24),
                _buildInsightsCard(),
                const SizedBox(height: 24),
                _buildSettingsCard(),
                const SizedBox(height: 60), // bottom nav clearance
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildSectionTitle(String title, {String? actionText, VoidCallback? onAction}) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(title, style: const TextStyle(color: ProfileScreen.textPrimary, fontSize: 20, fontWeight: FontWeight.bold)),
        if (actionText != null && onAction != null)
          GestureDetector(
            onTap: onAction,
            child: Text(
              actionText,
              style: const TextStyle(color: ProfileScreen.accentGreen, fontSize: 14, fontWeight: FontWeight.bold),
            ),
          ),
      ],
    );
  }

  Widget _buildHeaderCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: ProfileScreen.cardBg,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            height: 60, width: 60,
            decoration: BoxDecoration(
              color: ProfileScreen.accentGreen.withOpacity(0.2),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.person, color: ProfileScreen.accentGreen, size: 32),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Diya', style: TextStyle(color: ProfileScreen.textPrimary, fontSize: 22, fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                const Text('diya@example.com', style: TextStyle(color: ProfileScreen.textSecondary, fontSize: 14)),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.blue.withOpacity(0.15),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Text(_riskTag, style: const TextStyle(color: Colors.blueAccent, fontSize: 12, fontWeight: FontWeight.bold)),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                Text('Stability Score: $_stabilityScore/100', style: const TextStyle(color: ProfileScreen.accentGreen, fontSize: 13, fontWeight: FontWeight.w600)),
              ],
            ),
          ),
          GestureDetector(
            onTap: () async {
              // Open edit profile sheet passing states via routes or just standard Navigator since GoRouter isn't mapping sub-push dynamically right now without messing up user app state
              final currentPrefs = {
                'income': _income,
                'expenses': _expenses,
                'emergencyMonths': _emergencyMonths,
                'goalHorizon': _goalHorizon,
                'riskSlider': _riskSlider,
                'savingsHabit': _savingsHabit,
                'investmentKnowledge': _investmentKnowledge,
                'debtStatus': _debtStatus,
              };

              final result = await Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (context) => EditProfileScreen(initialPreferences: currentPrefs),
                ),
              );

              if (result != null) {
                setState(() {
                  _income = result['income'];
                  _expenses = result['expenses'];
                  _emergencyMonths = result['emergencyMonths'];
                  _goalHorizon = result['goalHorizon'];
                  _riskSlider = result['riskSlider'];
                  _savingsHabit = result['savingsHabit'];
                  _investmentKnowledge = result['investmentKnowledge'];
                  _debtStatus = result['debtStatus'];
                });
                _recalculateTargetStates();
                
                if (!mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Profile Updated', style: TextStyle(color: Colors.black)),
                    backgroundColor: ProfileScreen.accentGreen,
                    duration: Duration(seconds: 2),
                  ),
                );
              }
            },
            child: const Icon(Icons.edit, color: ProfileScreen.textSecondary, size: 20),
          ),
        ],
      ),
    );
  }

  Widget _buildAccountCard(AccountItem acc) {
    IconData icon;
    Color iconColor;
    if (acc.type == 'credit_card') {
      icon = Icons.credit_card;
      iconColor = Colors.orange;
    } else if (acc.type == 'wallet') {
      icon = Icons.account_balance_wallet;
      iconColor = Colors.teal;
    } else {
      icon = Icons.account_balance;
      iconColor = Colors.blueAccent;
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: ProfileScreen.cardBg,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(color: iconColor.withOpacity(0.15), borderRadius: BorderRadius.circular(12)),
            child: Icon(icon, color: iconColor, size: 24),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(acc.name, style: const TextStyle(color: ProfileScreen.textPrimary, fontSize: 16, fontWeight: FontWeight.bold)),
                const SizedBox(height: 4),
                Text(acc.maskedId, style: const TextStyle(color: ProfileScreen.textSecondary, fontSize: 13)),
              ],
            ),
          ),
          Text(_formatCurrency(acc.balance), style: const TextStyle(color: ProfileScreen.textPrimary, fontSize: 16, fontWeight: FontWeight.bold)),
          const SizedBox(width: 8),
          PopupMenuButton<String>(
            color: ProfileScreen.bgColor,
            icon: const Icon(Icons.more_vert, color: ProfileScreen.textSecondary),
            onSelected: (val) {
              if (val == 'edit') {
                _showAccountSheet(account: acc);
              } else if (val == 'delete') {
                _deleteAccount(acc.id);
              }
            },
            itemBuilder: (context) => [
              const PopupMenuItem(value: 'edit', child: Text('Edit', style: TextStyle(color: Colors.white))),
              const PopupMenuItem(value: 'delete', child: Text('Delete', style: TextStyle(color: Colors.redAccent))),
            ],
          ),
        ],
      ),
    );
  }



  Widget _buildInsightsCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: ProfileScreen.cardBg,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(color: ProfileScreen.accentGreen.withOpacity(0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.bolt, color: ProfileScreen.accentGreen, size: 24),
              SizedBox(width: 8),
              Text('Insights Snapshot', style: TextStyle(color: ProfileScreen.textPrimary, fontSize: 18, fontWeight: FontWeight.bold)),
            ],
          ),
          const SizedBox(height: 16),
          _buildInsightRow("Disposable Income", _formatCurrency(_disposableIncome)),
          const SizedBox(height: 12),
          _buildInsightRow("Savings Rate", "${_savingsRate.toStringAsFixed(1)}%"),
          const SizedBox(height: 12),
          _buildInsightRow("Risk Category", _riskTag),
        ],
      ),
    );
  }

  Widget _buildInsightRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(label, style: const TextStyle(color: ProfileScreen.textSecondary, fontSize: 15)),
        Text(value, style: const TextStyle(color: ProfileScreen.textPrimary, fontSize: 15, fontWeight: FontWeight.bold)),
      ],
    );
  }

  Widget _buildTextField(TextEditingController ctrl, String hint, {TextInputType? keyboardType}) {
    return TextField(
      controller: ctrl,
      keyboardType: keyboardType,
      style: const TextStyle(color: ProfileScreen.textPrimary),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(color: ProfileScreen.textSecondary),
        filled: true,
        fillColor: ProfileScreen.bgColor,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12), borderSide: BorderSide.none),
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
    );
  }

  Widget _buildSettingsCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: ProfileScreen.cardBg,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('Account Settings', style: TextStyle(color: ProfileScreen.textPrimary, fontSize: 18, fontWeight: FontWeight.bold)),
          const SizedBox(height: 16),
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.download, color: ProfileScreen.textPrimary),
            title: const Text('Export My Data', style: TextStyle(color: ProfileScreen.textPrimary)),
            onTap: () => ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Coming soon'))),
          ),
          const Divider(color: ProfileScreen.bgColor),
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.delete_forever, color: Colors.redAccent),
            title: const Text('Delete My Data', style: TextStyle(color: Colors.redAccent)),
            onTap: () {
              showDialog(
                context: context,
                builder: (ctx) => AlertDialog(
                  backgroundColor: ProfileScreen.cardBg,
                  title: const Text('Confirm Deletion', style: TextStyle(color: Colors.white)),
                  content: const Text('Are you sure you want to delete your data?', style: TextStyle(color: ProfileScreen.textSecondary)),
                  actions: [
                    TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel', style: TextStyle(color: ProfileScreen.textSecondary))),
                    TextButton(
                      onPressed: () {
                        Navigator.pop(ctx);
                        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Not implemented')));
                      },
                      child: const Text('Delete', style: TextStyle(color: Colors.redAccent)),
                    ),
                  ],
                ),
              );
            },
          ),
          const Divider(color: ProfileScreen.bgColor),
          ListTile(
            contentPadding: EdgeInsets.zero,
            leading: const Icon(Icons.logout, color: ProfileScreen.textSecondary),
            title: const Text('Logout', style: TextStyle(color: ProfileScreen.textSecondary)),
            onTap: () => ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Logout not implemented'))),
          ),
        ],
      ),
    );
  }
}
