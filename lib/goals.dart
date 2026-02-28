import 'package:flutter/material.dart';
import 'services/api_service.dart';

class GoalsScreen extends StatefulWidget {
  const GoalsScreen({Key? key}) : super(key: key);

  @override
  State<GoalsScreen> createState() => _GoalsScreenState();
}

class _GoalsScreenState extends State<GoalsScreen> {
  final ApiService _apiService = ApiService();
  final int _userId = 1; // TODO: wire to authenticated user

  GoalsListResponse? _goalsData;
  bool _isLoading = true;
  String? _error;

  // Theme Colors
  static const Color bgColor = Color(0xFF163339);
  static const Color accentGreen = Color(0xFF5DF22A);
  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Color(0xFF8BA5A8);
  static const Color textDark = Color(0xFF1D2F35);
  static const Color cardBg = Colors.white;
  static const Color dividerColor = Color(0xFFE5E9EA);

  @override
  void initState() {
    super.initState();
    _loadGoals();
  }

  Future<void> _loadGoals() async {
    try {
      final data = await _apiService.getGoals(userId: _userId);
      if (!mounted) return;
      setState(() {
        _goalsData = data;
        _isLoading = false;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Failed to load goals: $e';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: bgColor,
      body: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(),
              const SizedBox(height: 24),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20.0),
                child: _buildBodyContent(),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildHeader() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          const Text(
            'My Goals',
            style: TextStyle(
              color: textPrimary,
              fontSize: 28,
              fontWeight: FontWeight.bold,
            ),
          ),
          GestureDetector(
            onTap: () => _showCreateGoalDialog(context),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: accentGreen.withOpacity(0.15),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: accentGreen.withOpacity(0.5)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.add, color: accentGreen, size: 18),
                  SizedBox(width: 4),
                  Text(
                    'Add',
                    style: TextStyle(
                      color: accentGreen,
                      fontSize: 14,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBodyContent() {
    if (_isLoading) {
      return const Center(
        child: Padding(
          padding: EdgeInsets.symmetric(vertical: 40),
          child: CircularProgressIndicator(color: accentGreen),
        ),
      );
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              _error!,
              style: const TextStyle(color: textPrimary),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: _loadGoals,
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    final goals = _goalsData?.goals ?? [];

    return Column(
      children: [
        if (goals.isEmpty)
          Container(
            padding: const EdgeInsets.all(32),
            child: const Text(
              'No active goals. Create one to get started!',
              style: TextStyle(color: textSecondary, fontSize: 16),
              textAlign: TextAlign.center,
            ),
          )
        else
          ...goals.map((goal) => _buildGoalCard(goal)).toList(),
        const SizedBox(height: 40),
      ],
    );
  }

  Widget _buildGoalCard(GoalItem goal) {
    final timeline = goal.timeline;
    final statusText = _getStatusText(timeline.status);
    final daysLeft = timeline.monthsToDeadline > 0
        ? '${timeline.monthsToDeadline} mo'
        : 'Overdue';

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: cardBg,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: goal.statusColor.withOpacity(0.15),
                  shape: BoxShape.circle,
                ),
                child: Icon(
                  goal.icon,
                  color: goal.statusColor,
                  size: 28,
                ),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      goal.goalName,
                      style: const TextStyle(
                        color: textDark,
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      goal.deadline ?? 'No deadline',
                      style: const TextStyle(
                        color: Color(0xFFAAB8BA),
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: goal.statusColor.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(6),
                ),
                child: Text(
                  statusText.toUpperCase(),
                  style: TextStyle(
                    color: goal.statusColor,
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                    letterSpacing: 0.5,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                _formatCurrency(goal.currentAmount),
                style: const TextStyle(
                  color: textDark,
                  fontSize: 22,
                  fontWeight: FontWeight.bold,
                ),
              ),
              Text(
                'of ${_formatCurrency(goal.targetAmount)}',
                style: const TextStyle(
                  color: Color(0xFFAAB8BA),
                  fontSize: 16,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: (goal.progressPct / 100).clamp(0.0, 1.0),
              minHeight: 10,
              backgroundColor: const Color(0xFFF0F4F5),
              valueColor: AlwaysStoppedAnimation<Color>(goal.statusColor),
            ),
          ),
          const SizedBox(height: 20),
          const Divider(color: dividerColor, height: 1),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Monthly SIP',
                    style: TextStyle(
                      color: textSecondary,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    _formatCurrency(goal.monthlyContribution),
                    style: const TextStyle(
                      color: textDark,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  const Text(
                    'Feasibility',
                    style: TextStyle(
                      color: textSecondary,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${timeline.feasibilityPct.toStringAsFixed(0)}%',
                    style: TextStyle(
                      color: goal.statusColor,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  const Text(
                    'Time Left',
                    style: TextStyle(
                      color: textSecondary,
                      fontSize: 14,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    daysLeft,
                    style: const TextStyle(
                      color: textDark,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ],
          ),
          if (goal.timeline.runwayMonths != null)
            Padding(
              padding: const EdgeInsets.only(top: 16),
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: const Color(0xFFF5F7F8),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Icon(Icons.health_and_safety_outlined,
                        color: Color(0xFF4DD0E1), size: 18),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Emergency Coverage',
                          style: TextStyle(
                            color: textSecondary,
                            fontSize: 12,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '${goal.timeline.runwayMonths?.toStringAsFixed(1)} months of expenses',
                          style: const TextStyle(
                            color: textDark,
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }

  void _showCreateGoalDialog(BuildContext context) {
    final goalNameController = TextEditingController();
    final targetAmountController = TextEditingController();
    final currentSavedController = TextEditingController();
    final deadlineController = TextEditingController();
    String selectedType = 'custom';
    int selectedPriority = 2;
    bool isCreating = false;
    double? calculatedSip;

    showDialog(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setState) => AlertDialog(
          backgroundColor: cardBg,
          title: const Text(
            'Create New Goal',
            style: TextStyle(color: textDark, fontWeight: FontWeight.bold),
          ),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: goalNameController,
                  decoration: InputDecoration(
                    labelText: 'Goal Name',
                    hintText: 'e.g., Emergency Fund',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
                  ),
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  value: selectedType,
                  decoration: InputDecoration(
                    labelText: 'Goal Type',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
                  ),
                  items: const [
                    DropdownMenuItem(value: 'emergency_fund', child: Text('Emergency Fund')),
                    DropdownMenuItem(value: 'retirement', child: Text('Retirement')),
                    DropdownMenuItem(value: 'short_term', child: Text('Short Term')),
                    DropdownMenuItem(value: 'long_term', child: Text('Long Term')),
                    DropdownMenuItem(value: 'custom', child: Text('Custom')),
                  ],
                  onChanged: (value) => setState(() => selectedType = value ?? 'custom'),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: targetAmountController,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: InputDecoration(
                    labelText: 'Target Amount (₹)',
                    hintText: '100000',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
                  ),
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: currentSavedController,
                  keyboardType: const TextInputType.numberWithOptions(decimal: true),
                  decoration: InputDecoration(
                    labelText: 'Currently Saved (₹)',
                    hintText: '0',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
                  ),
                  onChanged: (_) => setState(() => calculatedSip = null), // Reset SIP when input changes
                ),
                const SizedBox(height: 16),
                TextField(
                  controller: deadlineController,
                  readOnly: true,
                  decoration: InputDecoration(
                    labelText: 'Deadline',
                    hintText: 'Tap to select',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
                    suffixIcon: const Icon(Icons.calendar_today),
                  ),
                  onTap: () async {
                    final selectedDate = await showDatePicker(
                      context: context,
                      initialDate: DateTime.now().add(const Duration(days: 365)),
                      firstDate: DateTime.now(),
                      lastDate: DateTime(2050),
                    );
                    if (selectedDate != null) {
                      final dateStr = selectedDate.toString().split(' ')[0];
                      setState(() {
                        deadlineController.text = dateStr;
                        calculatedSip = null; // Reset to recalculate
                      });
                    }
                  },
                ),
                if (calculatedSip != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 16),
                    child: Container(
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: accentGreen.withOpacity(0.1),
                        borderRadius: BorderRadius.circular(8),
                        border: Border.all(color: accentGreen.withOpacity(0.3)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          const Text(
                            'Calculated Monthly SIP:',
                            style: TextStyle(
                              color: textSecondary,
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text(
                            _formatCurrency(calculatedSip ?? 0),
                            style: TextStyle(
                              color: accentGreen,
                              fontSize: 18,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                const SizedBox(height: 16),
                ElevatedButton.icon(
                  onPressed: (targetAmountController.text.isNotEmpty &&
                          currentSavedController.text.isNotEmpty &&
                          deadlineController.text.isNotEmpty)
                      ? () => _calculateSip(
                            double.tryParse(targetAmountController.text) ?? 0,
                            double.tryParse(currentSavedController.text) ?? 0,
                            deadlineController.text,
                            setState,
                            (sip) => setState(() => calculatedSip = sip),
                          )
                      : null,
                  icon: const Icon(Icons.calculate),
                  label: const Text('Calculate SIP'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: accentGreen.withOpacity(0.3),
                  ),
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<int>(
                  value: selectedPriority,
                  decoration: InputDecoration(
                    labelText: 'Priority',
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 16),
                  ),
                  items: const [
                    DropdownMenuItem(value: 1, child: Text('High')),
                    DropdownMenuItem(value: 2, child: Text('Medium')),
                    DropdownMenuItem(value: 3, child: Text('Low')),
                  ],
                  onChanged: (value) => setState(() => selectedPriority = value ?? 2),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: isCreating ? null : () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: isCreating ? null : () => _createNewGoal(
                goalNameController.text,
                selectedType,
                targetAmountController.text,
                currentSavedController.text,
                deadlineController.text,
                selectedPriority,
                calculatedSip,
                context,
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: accentGreen,
              ),
              child: isCreating
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(
                        strokeWidth: 2,
                        valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                      ),
                    )
                  : const Text('Create'),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _calculateSip(
    double targetAmount,
    double currentSaved,
    String deadline,
    StateSetter setState,
    Function(double) onSipCalculated,
  ) async {
    try {
      // Simple calculation on client side: (target - saved) / months_remaining
      final deadlineDate = DateTime.parse(deadline);
      final now = DateTime.now();
      final monthsRemaining = ((deadlineDate.year - now.year) * 12 + (deadlineDate.month - now.month));
      
      if (monthsRemaining <= 0) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Deadline must be in the future')),
        );
        return;
      }
      
      final amountNeeded = targetAmount - currentSaved;
      if (amountNeeded <= 0) {
        onSipCalculated(0.0);
        return;
      }
      
      // Simple estimate (doesn't account for compound interest, server will do full calc)
      final estimatedSip = amountNeeded / monthsRemaining;
      onSipCalculated(estimatedSip);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error calculating SIP: $e')),
      );
    }
  }

  Future<void> _createNewGoal(
    String goalName,
    String goalType,
    String targetAmount,
    String currentSaved,
    String deadline,
    int priority,
    double? calculatedSip,
    BuildContext context,
  ) async {
    if (goalName.isEmpty || targetAmount.isEmpty || currentSaved.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please fill in all required fields')),
      );
      return;
    }

    try {
      final target = double.parse(targetAmount);
      final saved = double.parse(currentSaved);

      final response = await _apiService.createGoal(
        userId: _userId,
        goalName: goalName,
        goalType: goalType,
        targetAmount: target,
        currentSaved: saved,
        monthlyContribution: calculatedSip,
        deadline: deadline.isNotEmpty ? deadline : null,
        priority: priority,
      );

      if (!mounted) return;

      if (response['success'] == true) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              'Goal created! Monthly SIP: ${_formatCurrency(response['monthly_contribution'] ?? 0)}',
            ),
            duration: const Duration(seconds: 3),
          ),
        );
        Navigator.pop(context);
        _loadGoals(); // Refresh goals list
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: ${response['error'] ?? 'Unknown error'}')),
        );
      }
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error creating goal: $e')),
      );
    }
  }

  String _formatCurrency(double value) {
    final absValue = value.abs();
    String suffix = '';
    double displayValue = absValue;

    if (absValue >= 10000000) {
      displayValue = absValue / 10000000;
      suffix = ' Cr';
    } else if (absValue >= 100000) {
      displayValue = absValue / 100000;
      suffix = ' L';
    } else if (absValue >= 1000) {
      displayValue = absValue / 1000;
      suffix = ' k';
    }

    final formatted = displayValue >= 10
        ? displayValue.toStringAsFixed(0)
        : displayValue.toStringAsFixed(1);
    final prefix = value < 0 ? '-₹' : '₹';
    return '$prefix$formatted$suffix';
  }

  String _getStatusText(String status) {
    switch (status) {
      case 'early':
        return 'Ahead';
      case 'on_time':
        return 'On Track';
      case 'late':
        return 'Behind';
      default:
        return 'Unknown';
    }
  }
}
