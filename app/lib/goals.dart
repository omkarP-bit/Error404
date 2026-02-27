import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'models/goal.dart';
import 'models/goal_vm.dart';
import 'models/investment_overview_vm.dart';
import 'services/goals_investments_service.dart';
import 'services/local_goals_db.dart';
import 'services/goal_timeline_engine.dart';
import 'services/goal_allocation_engine.dart';
import 'services/local_user_settings.dart';
import 'services/local_momentum_db.dart';
import 'services/momentum_engine.dart';
import 'services/goal_probability_service.dart';

class GoalsScreen extends StatefulWidget {
  const GoalsScreen({Key? key}) : super(key: key);

  // Theme Colors
  static const Color bgColor = Color(0xFF163339); // Dark blue from dashboard
  static const Color accentGreen = Color(0xFF5DF22A);
  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Color(0xFF8BA5A8);
  static const Color textDark = Color(0xFF1D2F35);
  static const Color cardBg = Colors.white;
  static const Color dividerColor = Color(0xFFE5E9EA);

  @override
  State<GoalsScreen> createState() => _GoalsScreenState();
}

class _GoalsScreenState extends State<GoalsScreen> {
  final GoalsInvestmentsService _service = GoalsInvestmentsService();
  final LocalGoalsDB _dbService = LocalGoalsDB();
  final LocalUserSettings _userSettings = LocalUserSettings();
  final GoalAllocationEngine _allocationEngine = GoalAllocationEngine();
  final LocalMomentumDb _momentumDb = LocalMomentumDb();
  final MomentumEngine _momentumEngine = MomentumEngine();
  final GoalProbabilityService _probabilityService = GoalProbabilityService();
  InvestmentOverviewVM? _vm;
  MomentumResult? _momentumResult;
  List<GoalVM> _localGoals = [];
  double _monthlySurplus = 0.0;
  bool _emergencyComplete = true;
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    try {
      await _dbService.db;
      final surplus = await _userSettings.getMonthlySurplus();
      double defaultEmergencyTarget = surplus > 0 ? surplus * 3 : 50000.0;
      await _dbService.ensureEmergencyGoalExists(1, defaultTarget: defaultEmergencyTarget);
      
      final goals = await _dbService.fetchGoals(1);
      final vm = await _service.fetchGoalsAndInvestmentOverview();
      
      bool emergencyComplete = true;
      try {
        final eGoal = goals.firstWhere((g) => g.type == 'emergency_fund');
        if (eGoal.targetAmount <= 0) {
          emergencyComplete = false;
        } else {
          emergencyComplete = eGoal.savedAmount >= (eGoal.targetAmount * 0.80);
        }
      } catch (_) {}

      await _momentumDb.ensureTablesExist();
      final String currentMonthKey = _momentumDb.monthKeyFromDate(DateTime.now());
      final lastActivities = await _momentumDb.fetchLastMonths(userId: 1, windowMonths: 6);
      final momentum = _momentumEngine.compute(
        lastMonths: lastActivities,
        currentMonthKey: currentMonthKey,
        windowMonths: 6,
      );

      setState(() {
        _vm = vm;
        _momentumResult = momentum;
        _monthlySurplus = surplus;
        _emergencyComplete = emergencyComplete;
        _localGoals = goals.map(_mapGoalToVM).toList();
        _isLoading = false;
      });
      
      // Async trigger for ML probability
      _computeProbabilitiesBackground(goals);
    } catch (e) {
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  Future<void> _computeProbabilitiesBackground(List<Goal> goals) async {
    bool updated = false;
    for (var g in goals) {
      if (g.feasibilityScore == null) {
        await _probabilityService.computeAndSaveFeasibility(g);
        updated = true;
      }
    }
    if (updated && mounted) {
      final newGoals = await _dbService.fetchGoals(1);
      setState(() {
        _localGoals = newGoals.map(_mapGoalToVM).toList();
      });
    }
  }

  GoalVM _mapGoalToVM(Goal goal) {
    double progress = goal.targetAmount > 0 ? (goal.savedAmount / goal.targetAmount).clamp(0.0, 1.0) : 0.0;
    String statusLabel = "IN PROGRESS";
    Color statusColor = const Color(0xFF4285F4);
    
    if (goal.deadline != null) {
      statusLabel = progress >= 0.5 ? "ON TRACK" : "BEHIND";
      statusColor = progress >= 0.5 ? const Color(0xFF34A853) : const Color(0xFFEA4335);
    }

    int? monthsLeft;
    if (goal.deadline != null) {
      final now = DateTime.now();
      monthsLeft = goal.deadline!.month - now.month + 12 * (goal.deadline!.year - now.year);
      if (monthsLeft < 1) monthsLeft = 1;
    }

    double monthlyRequired = 0.0;
    if (monthsLeft != null && monthsLeft > 0) {
      monthlyRequired = ((goal.targetAmount - goal.savedAmount) / monthsLeft).clamp(0.0, double.infinity).ceilToDouble();
    } else {
      monthlyRequired = goal.monthlyContribution;
    }

    IconData icon = Icons.star;
    Color iconColor = Colors.blue;
    Color iconBgColor = Colors.blue.withOpacity(0.1);
    
    switch (goal.type) {
      case 'emergency_fund':
        icon = Icons.security;
        iconColor = Colors.green;
        iconBgColor = Colors.green.withOpacity(0.1);
        break;
      case 'short_term':
        icon = Icons.flight_takeoff;
        iconColor = Colors.orange;
        iconBgColor = Colors.orange.withOpacity(0.1);
        break;
      case 'long_term':
        icon = Icons.home;
        iconColor = Colors.purple;
        iconBgColor = Colors.purple.withOpacity(0.1);
        break;
      case 'retirement':
        icon = Icons.beach_access;
        iconColor = Colors.teal;
        iconBgColor = Colors.teal.withOpacity(0.1);
        break;
    }

    return GoalVM(
      goalId: goal.id ?? 0,
      goalName: goal.name,
      goalType: goal.type,
      targetAmount: goal.targetAmount,
      savedAmount: goal.savedAmount,
      monthlyContribution: goal.monthlyContribution,
      deadline: goal.deadline,
      priority: goal.priority,
      progress: progress,
      monthsLeft: monthsLeft,
      monthlyRequired: monthlyRequired,
      statusLabel: statusLabel,
      statusColor: statusColor,
      icon: icon,
      iconColor: iconColor,
      iconBgColor: iconBgColor,
      feasibilityScore: goal.feasibilityScore,
      feasibilityNote: goal.feasibilityNote,
    );
  }

  void _showAddGoalBottomSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => _AddGoalForm(
        onGoalAdded: () {
          _loadData(); // Re-fetch data after add
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Goal created successfully'), backgroundColor: GoalsScreen.bgColor),
          );
        },
      ),
    );
  }

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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: GoalsScreen.bgColor,
      body: SafeArea(
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              _buildHeader(),
              const SizedBox(height: 24),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 20.0),
                child: _isLoading
                    ? const Center(child: Padding(
                        padding: EdgeInsets.all(40.0),
                        child: CircularProgressIndicator(color: GoalsScreen.accentGreen),
                      ))
                    : _error != null
                        ? _buildErrorCard()
                        : Column(
                            children: [
                              if (_localGoals.isEmpty)
                                _buildEmptyGoalsCard()
                              else ...[
                                if (!_emergencyComplete) ...[
                                  _buildEmergencyBanner(),
                                  const SizedBox(height: 16),
                                ],
                                if (_momentumResult != null) ...[
                                  _buildMomentumCard(),
                                  const SizedBox(height: 16),
                                ],
                                _buildAutoAllocationCard(),
                                const SizedBox(height: 16),
                                ..._localGoals.map((g) => Padding(
                                      padding: const EdgeInsets.only(bottom: 16),
                                      child: _buildGoalCard(g),
                                    )),
                              ],
                              const SizedBox(height: 16),
                              _buildInvestmentPlanningCard(_vm!),
                              const SizedBox(height: 40), // Space before bottom nav
                            ],
                          ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildGoalCard(GoalVM goal) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: GoalsScreen.cardBg,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      goal.goalName,
                      style: const TextStyle(
                        color: GoalsScreen.textDark,
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${goal.goalType.replaceAll('_', ' ').toTitleCase()} Goal',
                      style: const TextStyle(
                        color: GoalsScreen.textSecondary,
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: goal.iconBgColor,
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Icon(goal.icon, color: goal.iconColor, size: 24),
              ),
            ],
          ),
          const SizedBox(height: 16),
          LinearProgressIndicator(
            value: goal.progress,
            backgroundColor: GoalsScreen.progressBg,
            valueColor: AlwaysStoppedAnimation<Color>(goal.statusColor),
            borderRadius: BorderRadius.circular(10),
            minHeight: 8,
          ),
          const SizedBox(height: 10),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                '${(goal.progress * 100).toStringAsFixed(0)}% Achieved',
                style: const TextStyle(
                  color: GoalsScreen.textSecondary,
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                ),
              ),
              Text(
                goal.statusLabel,
                style: TextStyle(
                  color: goal.statusColor,
                  fontSize: 12,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              _buildGoalStat('Target', _formatCurrency(goal.targetAmount)),
              _buildGoalStat('Saved', _formatCurrency(goal.savedAmount)),
              _buildGoalStat('Monthly', _formatCurrency(goal.monthlyRequired)),
            ],
          ),
          if (goal.feasibilityScore != null) ...[
            const SizedBox(height: 16),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text(
                  'Feasibility Score',
                  style: TextStyle(
                    color: GoalsScreen.textSecondary,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF5F7F8),
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Text(
                    '${goal.feasibilityScore!.toStringAsFixed(0)}/100',
                    style: const TextStyle(
                      color: GoalsScreen.textDark,
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                    ),
                  ),
                ),
              ],
            ),
          ],
          if (goal.feasibilityNote != null) ...[
            const SizedBox(height: 16),
            Text(
              goal.feasibilityNote!,
              style: const TextStyle(
                color: GoalsScreen.textSecondary,
                fontSize: 13,
                fontStyle: FontStyle.italic,
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildErrorCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: GoalsScreen.cardBg,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Center(
        child: Text(
          'Error: $_error',
          style: const TextStyle(color: Colors.redAccent),
          textAlign: TextAlign.center,
        ),
      ),
    );
  }

  Widget _buildEmptyGoalsCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: GoalsScreen.cardBg,
        borderRadius: BorderRadius.circular(24),
      ),
      child: const Center(
        child: Text(
          'No goals yet. Tap Add to create one.',
          style: TextStyle(color: GoalsScreen.textDark, fontSize: 16),
          textAlign: TextAlign.center,
        ),
      ),
    );
  }

  Widget _buildMomentumCard() {
    final res = _momentumResult!;
    int streakDays = res.streakMonths * 30; // approx conversion

    String headlineText = res.streakMonths == 0 
        ? "No streak yet — start this month!" 
        : "🔥 $streakDays day saving streak";

    int shownFires = res.streakMonths.clamp(0, 7);
    int extraFires = res.streakMonths - shownFires;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: GoalsScreen.cardBg,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // TOP ROW: Pill + Fire Icons
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  color: Colors.orange.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: const Text(
                  '🔥 STREAK',
                  style: TextStyle(
                    color: Colors.orange,
                    fontWeight: FontWeight.bold,
                    fontSize: 12,
                  ),
                ),
              ),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (res.streakMonths == 0)
                    ...List.generate(3, (_) => Padding(
                      padding: const EdgeInsets.only(left: 2),
                      child: Icon(Icons.local_fire_department, size: 20, color: Colors.grey.withOpacity(0.35)),
                    )),
                  if (res.streakMonths > 0)
                    for (int i = 0; i < shownFires; i++)
                      const Padding(
                        padding: EdgeInsets.only(left: 2),
                        child: Icon(Icons.local_fire_department, size: 20, color: Colors.orange),
                      ),
                  if (extraFires > 0)
                    Padding(
                      padding: const EdgeInsets.only(left: 6),
                      child: Text('+$extraFires', style: const TextStyle(color: GoalsScreen.textSecondary, fontWeight: FontWeight.w700)),
                    ),
                ],
              ),
            ],
          ),
          const SizedBox(height: 14),

          // TITLE ROW
          const Text(
            'Momentum',
            style: TextStyle(
              color: GoalsScreen.textDark,
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 2),
          const Text(
            'Behavior-based saving score',
            style: TextStyle(
              color: GoalsScreen.textSecondary,
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 14),

          // HEADLINE
          Text(
            headlineText,
            style: const TextStyle(
              color: GoalsScreen.textDark,
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 14),

          // SCORE ROW
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Momentum Score',
                style: TextStyle(
                  color: GoalsScreen.textSecondary,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: const Color(0xFFF5F7F8),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Text(
                  '⚡ ${res.score}/100',
                  style: const TextStyle(
                    color: GoalsScreen.textDark,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),

          // BOTTOM STATS CONTAINER
          Container(
            padding: const EdgeInsets.symmetric(vertical: 12),
            decoration: BoxDecoration(
              color: const Color(0xFFF5F7F8),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceEvenly,
              children: [
                _buildStatColumn('Consistency', '${res.consistencyPct.toStringAsFixed(0)}%'),
                _buildStatColumn('Missed', '${res.missedMonths}'),
                _buildStatColumn('Window', '6 mo'),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatColumn(String label, String value) {
    return Column(
      children: [
        Text(
          label,
          style: const TextStyle(
            color: GoalsScreen.textSecondary,
            fontSize: 12,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          value,
          style: const TextStyle(
            color: GoalsScreen.textDark,
            fontSize: 14,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  Widget _buildEmergencyBanner() {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: GoalsScreen.cardBg,
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: Colors.orange.withOpacity(0.5)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Build emergency fund first',
            style: TextStyle(
              color: Colors.orange,
              fontSize: 16,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'Complete 80% of your emergency target to unlock full goal allocations.',
            style: TextStyle(
              color: GoalsScreen.textSecondary,
              fontSize: 13,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAutoAllocationCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: GoalsScreen.cardBg,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Auto Allocation',
            style: TextStyle(
              color: GoalsScreen.textDark,
              fontSize: 20,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 4),
          const Text(
            'Split surplus across goals by priority',
            style: TextStyle(
              color: GoalsScreen.textSecondary,
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('Monthly Surplus', style: TextStyle(color: GoalsScreen.textSecondary, fontSize: 13)),
                  const SizedBox(height: 4),
                  Text(_formatCurrency(_monthlySurplus), style: const TextStyle(color: GoalsScreen.textDark, fontSize: 18, fontWeight: FontWeight.bold)),
                ],
              ),
              OutlinedButton(
                onPressed: _showSetSurplusDialog,
                style: OutlinedButton.styleFrom(
                  side: const BorderSide(color: GoalsScreen.dividerColor),
                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                ),
                child: const Text('Set', style: TextStyle(color: GoalsScreen.textDark)),
              ),
            ],
          ),
          const SizedBox(height: 16),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: GoalsScreen.accentGreen.withOpacity(0.15),
                foregroundColor: GoalsScreen.accentGreen,
                elevation: 0,
                padding: const EdgeInsets.symmetric(vertical: 12),
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              ),
              onPressed: _monthlySurplus > 0 ? _runAutoAllocation : null,
              child: const Text('Auto-Allocate SIP', style: TextStyle(fontWeight: FontWeight.bold)),
            ),
          ),
        ],
      ),
    );
  }

  void _showSetSurplusDialog() {
    final controller = TextEditingController(text: _monthlySurplus > 0 ? _monthlySurplus.toStringAsFixed(0) : '');
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Set Monthly Surplus'),
        content: TextField(
          controller: controller,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(hintText: 'e.g. 50000'),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text('Cancel')),
          TextButton(
            onPressed: () async {
              final val = double.tryParse(controller.text) ?? 0;
              await _userSettings.setMonthlySurplus(val);
              setState(() => _monthlySurplus = val);
              Navigator.pop(context);
            },
            child: const Text('Save'),
          ),
        ],
      ),
    );
  }

  Future<void> _runAutoAllocation() async {
    try {
      final rawGoals = await _dbService.fetchGoals(1);
      final result = _allocationEngine.allocate(
        monthlySurplus: _monthlySurplus,
        activeGoals: rawGoals,
      );
      
      await _dbService.updateMonthlyContributionBulk(result.goalIdToMonthlyContribution);
      
      double totalSip = result.totalAllocated;
      if (totalSip > 0) {
        await _momentumDb.upsertContribution(
          userId: 1,
          monthKey: _momentumDb.monthKeyFromDate(DateTime.now()),
          totalSipAmount: totalSip,
        );
      }
      
      await _loadData();
      
      if (mounted) {
        if (!_emergencyComplete) {
          double eAlloc = 0.0;
          try {
            int eId = rawGoals.firstWhere((g) => g.type == 'emergency_fund').id!;
            eAlloc = result.goalIdToMonthlyContribution[eId] ?? 0.0;
          } catch (_) {}
          
          double otherAlloc = result.totalAllocated - eAlloc;
          if (otherAlloc < 0) otherAlloc = 0;
          
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Emergency fund prioritized: ${_formatCurrency(eAlloc)} → Emergency, ${_formatCurrency(otherAlloc)} → Other goals'),
              backgroundColor: GoalsScreen.bgColor,
            ),
          );
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text('Allocated ${_formatCurrency(result.totalAllocated)} across goals by priority'),
              backgroundColor: GoalsScreen.bgColor,
            ),
          );
        }
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Allocation failed: $e'), backgroundColor: Colors.red),
        );
      }
    }
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
              color: GoalsScreen.textPrimary,
              fontSize: 28,
              fontWeight: FontWeight.bold,
            ),
          ),
          GestureDetector(
            onTap: _showAddGoalBottomSheet,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: GoalsScreen.accentGreen.withOpacity(0.15),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: GoalsScreen.accentGreen.withOpacity(0.5)),
              ),
              child: const Row(
                children: [
                  Icon(Icons.add, color: GoalsScreen.accentGreen, size: 18),
                  SizedBox(width: 4),
                  Text(
                    'Add',
                    style: TextStyle(
                      color: GoalsScreen.accentGreen,
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

  Widget _buildGoalCard(GoalVM goal) {
    String _formatDate(DateTime date) {
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      return '${months[date.month - 1]} ${date.year}';
    }
    
    String deadlineStr = goal.deadline != null 
        ? _formatDate(goal.deadline!)
        : 'No deadline';

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: GoalsScreen.cardBg,
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
                  color: goal.iconBgColor,
                  shape: BoxShape.circle,
                ),
                child: Icon(goal.icon, color: goal.iconColor, size: 28),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      goal.goalName,
                      style: const TextStyle(
                        color: GoalsScreen.textDark,
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Deadline: $deadlineStr',
                      style: const TextStyle(
                        color: Color(0xFFAAB8BA),
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 8),
                    if (goal.feasibilityScore != null)
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: GoalsScreen.accentGreen.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: GoalsScreen.accentGreen.withOpacity(0.3)),
                        ),
                        child: Text(
                          '🎯 ${(goal.feasibilityScore! * 100).round()}%',
                          style: const TextStyle(
                            color: GoalsScreen.accentGreen,
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      )
                    else
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: Colors.grey.withOpacity(0.1),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: Colors.grey.withOpacity(0.3)),
                        ),
                        child: const Text(
                          '🎯 Calculating…',
                          style: TextStyle(
                            color: Colors.grey,
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
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
                  goal.statusLabel,
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
                _formatCurrency(goal.savedAmount),
                style: const TextStyle(
                  color: GoalsScreen.textDark,
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
              value: goal.progress,
              minHeight: 10,
              backgroundColor: const Color(0xFFF0F4F5),
              valueColor: AlwaysStoppedAnimation<Color>(goal.statusColor),
            ),
          ),
          const SizedBox(height: 20),
          const Divider(color: GoalsScreen.dividerColor, height: 1),
          const SizedBox(height: 16),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Monthly required',
                style: TextStyle(
                  color: GoalsScreen.textSecondary,
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                ),
              ),
              Text(
                '${_formatCurrency(goal.monthlyRequired)}/mo',
                style: const TextStyle(
                  color: GoalsScreen.textDark,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Your SIP',
                style: TextStyle(
                  color: GoalsScreen.textSecondary,
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                ),
              ),
              Text(
                '${_formatCurrency(goal.monthlyContribution)}/mo',
                style: const TextStyle(
                  color: GoalsScreen.textDark,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildTimelineWidget(goal),
        ],
      ),
    );
  }

  Widget _buildTimelineWidget(GoalVM goal) {
    int? monthsToDeadline;
    if (goal.deadline != null) {
      final now = DateTime.now();
      monthsToDeadline = (goal.deadline!.year - now.year) * 12 + goal.deadline!.month - now.month;
      if (monthsToDeadline < 0) monthsToDeadline = 0;
    }

    final timeline = GoalTimelineEngine().simulate(
      targetAmount: goal.targetAmount,
      savedAmount: goal.savedAmount,
      monthlyContribution: goal.monthlyContribution,
      deadline: goal.deadline,
      annualExpectedReturn: GoalTimelineEngine.expectedReturnForGoal(
        goalType: goal.goalType,
        monthsToDeadline: monthsToDeadline,
      ),
    );

    List<Widget> columnChildren = [];

    if (timeline.monthsToTarget == 999) {
      columnChildren.add(_buildTimelineRow('Timeline', 'Not set (add contribution)'));
    } else if (timeline.monthsToTarget == 0) {
      columnChildren.add(_buildTimelineRow('Timeline', 'Achieved'));
    } else {
      columnChildren.add(_buildTimelineRow('At current pace', '${timeline.monthsToTarget} months'));
    }

    if (timeline.hasDeadline) {
      columnChildren.add(const SizedBox(height: 8));
      columnChildren.add(_buildTimelineRow('Deadline', '${timeline.monthsToDeadline} months'));
      
      columnChildren.add(const SizedBox(height: 8));
      if (timeline.monthsToTarget != 999 && timeline.monthsToTarget != 0) {
        String deltaText;
        if (timeline.deltaMonths! > 0) {
          deltaText = "You're ${timeline.deltaMonths} months late";
        } else if (timeline.deltaMonths! == 0) {
          deltaText = "On time";
        } else {
          deltaText = "Ahead by ${timeline.deltaMonths!.abs()} months";
        }
        columnChildren.add(_buildTimelineRow('Status', deltaText));
      }
    }

    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: const Color(0xFFF5F7F8),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: columnChildren,
      ),
    );
  }

  Widget _buildTimelineRow(String label, String value) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(
          label,
          style: const TextStyle(
            color: GoalsScreen.textSecondary,
            fontSize: 13,
            fontWeight: FontWeight.w500,
          ),
        ),
        Text(
          value,
          style: const TextStyle(
            color: GoalsScreen.textDark,
            fontSize: 13,
            fontWeight: FontWeight.bold,
          ),
        ),
      ],
    );
  }

  Widget _buildInvestmentPlanningCard(InvestmentOverviewVM vm) {
    int equity = vm.allocation["Equity (Index + Large Cap)"] ?? 0;
    int debt = vm.allocation["Debt/Liquid"] ?? 0;
    int gold = vm.allocation["Gold"] ?? 0;
    int intl = vm.allocation["International"] ?? 0;

    return Container(
      padding: const EdgeInsets.all(24),
      decoration: BoxDecoration(
        color: GoalsScreen.cardBg,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Investment Planning',
            style: TextStyle(
              color: GoalsScreen.textDark,
              fontSize: 22,
              fontWeight: FontWeight.bold,
            ),
          ),
          const SizedBox(height: 6),
          const Text(
            'Smart allocation, no stock picking',
            style: TextStyle(
              color: GoalsScreen.textSecondary,
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 24),
          
          // Readiness Strip
          Container(
            width: double.infinity,
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: const Color(0xFFF5F7F8),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                  decoration: BoxDecoration(
                    color: vm.investmentAllowed 
                        ? GoalsScreen.accentGreen.withOpacity(0.15)
                        : Colors.orange.withOpacity(0.15),
                    borderRadius: BorderRadius.circular(6),
                  ),
                  child: Text(
                    vm.investmentAllowed ? "INVESTING UNLOCKED" : "INVESTING RESTRICTED",
                    style: TextStyle(
                      color: vm.investmentAllowed ? const Color(0xFF00C853) : Colors.orange,
                      fontWeight: FontWeight.bold,
                      fontSize: 10,
                    ),
                  ),
                ),
                if (vm.gateReasons.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    vm.gateReasons.take(2).join('\n'),
                    style: const TextStyle(
                      color: GoalsScreen.textSecondary,
                      fontSize: 12,
                    ),
                  ),
                ],
              ],
            ),
          ),
          const SizedBox(height: 24),

          Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: const Color(0xFFF5F7F8),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              children: [
                _buildRiskTab('Conservative', vm.riskProfile == 'conservative'),
                _buildRiskTab('Moderate', vm.riskProfile == 'moderate'),
                _buildRiskTab('Aggressive', vm.riskProfile == 'aggressive'),
              ],
            ),
          ),
          const SizedBox(height: 30),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              const Text(
                'Suggested Monthly SIP',
                style: TextStyle(
                  color: GoalsScreen.textSecondary,
                  fontSize: 14,
                  fontWeight: FontWeight.w500,
                ),
              ),
              Text(
                _formatCurrency(vm.safeSipBudget),
                style: const TextStyle(
                  color: GoalsScreen.textDark,
                  fontSize: 26,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          _buildMultiColorProgressBar(equity, debt, gold, intl),
          const SizedBox(height: 20),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  children: [
                    if (equity > 0) _buildAssetClassLegend(const Color(0xFF4285F4), 'Equity ($equity%)'),
                    const SizedBox(height: 12),
                    if (debt > 0) _buildAssetClassLegend(const Color(0xFF34A853), 'Debt ($debt%)'),
                  ],
                ),
              ),
              Expanded(
                child: Column(
                  children: [
                    if (gold > 0) _buildAssetClassLegend(const Color(0xFFFBBC04), 'Gold ($gold%)'),
                    const SizedBox(height: 12),
                    if (intl > 0) _buildAssetClassLegend(const Color(0xFFA55EED), 'International ($intl%)'),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 24),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: const Color(0xFFF5F7F8),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(12),
                  decoration: const BoxDecoration(
                    color: Color(0xFFE5F9EF),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(Icons.trending_up, color: Colors.teal, size: 24),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Expected Return',
                        style: TextStyle(
                          color: GoalsScreen.textSecondary,
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        vm.expectedReturnText,
                        style: const TextStyle(
                          color: GoalsScreen.textDark,
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    const Text(
                      'Probability',
                      style: TextStyle(
                        color: GoalsScreen.textSecondary,
                        fontSize: 13,
                        fontWeight: FontWeight.w500,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      vm.probabilityText,
                      style: TextStyle(
                        color: GoalsScreen.accentGreen.withGreen(180),
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),

          // Hidden Wealth Detector
          if (vm.hiddenWealthTop3.isNotEmpty) ...[
            const SizedBox(height: 24),
            const Divider(color: GoalsScreen.dividerColor, height: 1),
            const SizedBox(height: 24),
            const Text(
              'Hidden Wealth Detector',
              style: TextStyle(
                color: GoalsScreen.textDark,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'We found ${_formatCurrency(vm.hiddenWealthUnlockMonthly)}/month you can unlock',
              style: const TextStyle(
                color: GoalsScreen.textSecondary,
                fontSize: 13,
                fontWeight: FontWeight.w500,
              ),
            ),
            const SizedBox(height: 16),
            ...vm.hiddenWealthTop3.map((op) => Container(
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: const Color(0xFFF5F7F8),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Expanded(
                        child: Text(
                          op.label,
                          style: const TextStyle(
                            color: GoalsScreen.textDark,
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ),
                      Text(
                        '+${_formatCurrency(op.unlockMonthly)}/mo',
                        style: const TextStyle(
                          color: Color(0xFF00C853),
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                )),
            if (vm.monthsSavedForTopGoal > 0) ...[
              const SizedBox(height: 4),
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: GoalsScreen.accentGreen.withOpacity(0.1),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: GoalsScreen.accentGreen.withOpacity(0.3)),
                ),
                child: Text(
                  'Reach your top goal ${vm.monthsSavedForTopGoal} months sooner',
                  textAlign: TextAlign.center,
                  style: const TextStyle(
                    color: Color(0xFF00C853),
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ],

        ],
      ),
    );
  }

  Widget _buildRiskTab(String label, bool isSelected) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12),
        decoration: BoxDecoration(
          color: isSelected ? Colors.white : Colors.transparent,
          borderRadius: BorderRadius.circular(12),
          boxShadow: isSelected
              ? [
                  BoxShadow(
                    color: Colors.black.withOpacity(0.05),
                    blurRadius: 4,
                    offset: const Offset(0, 2),
                  ),
                ]
              : null,
        ),
        alignment: Alignment.center,
        child: Text(
          label,
          style: TextStyle(
            color: isSelected ? GoalsScreen.textDark : const Color(0xFFAAB8BA),
            fontSize: 14,
            fontWeight: isSelected ? FontWeight.bold : FontWeight.w600,
          ),
        ),
      ),
    );
  }

  Widget _buildMultiColorProgressBar(int equity, int debt, int gold, int intl) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: SizedBox(
        height: 16,
        child: Row(
          children: [
            if (equity > 0) Expanded(flex: equity, child: Container(color: const Color(0xFF4285F4))),
            if (debt > 0) Expanded(flex: debt, child: Container(color: const Color(0xFF34A853))),
            if (gold > 0) Expanded(flex: gold, child: Container(color: const Color(0xFFFBBC04))),
            if (intl > 0) Expanded(flex: intl, child: Container(color: const Color(0xFFA55EED))),
          ],
        ),
      ),
    );
  }

  Widget _buildAssetClassLegend(Color color, String label) {
    return Row(
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: color,
            shape: BoxShape.circle,
          ),
        ),
        const SizedBox(width: 8),
        Expanded(
          child: Text(
            label,
            style: const TextStyle(
              color: GoalsScreen.textSecondary,
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}

class _AddGoalForm extends StatefulWidget {
  final VoidCallback onGoalAdded;

  const _AddGoalForm({Key? key, required this.onGoalAdded}) : super(key: key);

  @override
  State<_AddGoalForm> createState() => _AddGoalFormState();
}

class _AddGoalFormState extends State<_AddGoalForm> {
  final _formKey = GlobalKey<FormState>();
  final _nameController = TextEditingController();
  final _targetController = TextEditingController();
  final _savedController = TextEditingController(text: '0');
  final _monthlyController = TextEditingController();

  String _type = 'short_term';
  int _priority = 2; // Medium
  DateTime? _deadline;

  @override
  void dispose() {
    _nameController.dispose();
    _targetController.dispose();
    _savedController.dispose();
    _monthlyController.dispose();
    super.dispose();
  }

  void _save() async {
    if (_formKey.currentState!.validate()) {
      final targetAmount = double.tryParse(_targetController.text) ?? 0;
      final savedAmount = double.tryParse(_savedController.text) ?? 0;
      double monthlyContribution = double.tryParse(_monthlyController.text) ?? 0;
      // We no longer forcefully auto-calculate monthlyContribution if the user leaves it blank.
      // We store what they entered (0 if blank) so the simulation engine can say "Not set".

      final goal = Goal(
        userId: 1,
        name: _nameController.text.trim(),
        type: _type,
        targetAmount: targetAmount,
        savedAmount: savedAmount,
        monthlyContribution: monthlyContribution,
        deadline: _deadline,
        priority: _priority,
        status: 'active',
      );

      try {
        await LocalGoalsDB().insertGoal(goal);
        
        if (monthlyContribution > 0) {
           final rawGoals = await LocalGoalsDB().fetchGoals(1);
           double total = 0;
           for(var g in rawGoals) {
               if(g.status == 'active') total += g.monthlyContribution;
           }
           await LocalMomentumDb().upsertContribution(
               userId: 1,
               monthKey: LocalMomentumDb().monthKeyFromDate(DateTime.now()),
               totalSipAmount: total,
           );
        }

        if (mounted) {
          Navigator.pop(context);
          widget.onGoalAdded();
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Error saving goal: $e'), backgroundColor: Colors.red),
          );
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
        top: 24, left: 24, right: 24,
      ),
      decoration: const BoxDecoration(
        color: GoalsScreen.cardBg,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      child: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Add Goal', style: TextStyle(fontSize: 22, fontWeight: FontWeight.bold, color: GoalsScreen.textDark)),
              const SizedBox(height: 16),
              TextFormField(
                controller: _nameController,
                decoration: InputDecoration(labelText: 'Goal Name', border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
                validator: (val) => val == null || val.trim().isEmpty ? 'Required' : null,
              ),
              const SizedBox(height: 16),
              DropdownButtonFormField<String>(
                value: _type,
                decoration: InputDecoration(labelText: 'Goal Type', border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
                items: const [
                  DropdownMenuItem(value: 'emergency_fund', child: Text('Emergency Fund')),
                  DropdownMenuItem(value: 'short_term', child: Text('Short Term')),
                  DropdownMenuItem(value: 'long_term', child: Text('Long Term')),
                  DropdownMenuItem(value: 'retirement', child: Text('Retirement')),
                  DropdownMenuItem(value: 'custom', child: Text('Custom')),
                ],
                onChanged: (val) => setState(() => _type = val!),
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: TextFormField(
                      controller: _targetController,
                      keyboardType: TextInputType.number,
                      decoration: InputDecoration(labelText: 'Target Amount', border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
                      validator: (val) => (double.tryParse(val ?? '') ?? 0) <= 0 ? 'Must be > 0' : null,
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: TextFormField(
                      controller: _savedController,
                      keyboardType: TextInputType.number,
                      decoration: InputDecoration(labelText: 'Current Saved', border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: InkWell(
                      onTap: () async {
                        final date = await showDatePicker(
                          context: context,
                          initialDate: DateTime.now().add(const Duration(days: 30)),
                          firstDate: DateTime.now(),
                          lastDate: DateTime(2050),
                        );
                        if (date != null) setState(() => _deadline = date);
                      },
                      child: InputDecorator(
                        decoration: InputDecoration(labelText: 'Deadline', border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
                        child: Text(_deadline == null ? 'Not set' : DateFormat('MMM yyyy').format(_deadline!)),
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: DropdownButtonFormField<int>(
                      value: _priority,
                      decoration: InputDecoration(labelText: 'Priority', border: OutlineInputBorder(borderRadius: BorderRadius.circular(12))),
                      items: const [
                        DropdownMenuItem(value: 1, child: Text('High (1)')),
                        DropdownMenuItem(value: 2, child: Text('Medium (2)')),
                        DropdownMenuItem(value: 3, child: Text('Low (3)')),
                      ],
                      onChanged: (val) => setState(() => _priority = val!),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              TextFormField(
                controller: _monthlyController,
                keyboardType: TextInputType.number,
                decoration: InputDecoration(
                  labelText: 'Monthly Contribution (Optional)', 
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                  helperText: 'Used for timeline simulation',
                ),
              ),
              const SizedBox(height: 24),
              SizedBox(
                width: double.infinity,
                child: ElevatedButton(
                  style: ElevatedButton.styleFrom(
                    backgroundColor: GoalsScreen.bgColor,
                    padding: const EdgeInsets.symmetric(vertical: 16),
                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                  ),
                  onPressed: _save,
                  child: const Text('Save Goal', style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white)),
                ),
              ),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}
