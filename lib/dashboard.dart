import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'services/api_service.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({Key? key}) : super(key: key);

  // Theme Colors based on the provided screenshots
  static const Color bgColor = Color(0xFF163339);
  static const Color accentGreen = Color(0xFF5DF22A);
  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Color(0xFF8BA5A8);

  static const Color whiteCardColor = Colors.white;
  static const Color darkCardColor = Color(0xFF21444A);
  static const Color textDark = Color(0xFF1D2F35);

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _ComponentMeta {
  const _ComponentMeta({
    required this.key,
    required this.title,
    required this.description,
    required this.icon,
    required this.color,
    required this.weightLabel,
  });

  final String key;
  final String title;
  final String description;
  final IconData icon;
  final Color color;
  final String weightLabel;
}

class _DashboardScreenState extends State<DashboardScreen> {
  final ApiService _apiService = ApiService();
  final int _userId = 1; // TODO: wire to authenticated user

  DashboardSummary? _summary;
  bool _isLoading = true;
  String? _error;

  static const List<_ComponentMeta> _componentMeta = [
    _ComponentMeta(
      key: 'savings_rate',
      title: 'Savings Rate',
      description: 'Monthly savings ÷ income. Higher means more surplus.',
      icon: Icons.savings_outlined,
      color: Color(0xFF5DF22A),
      weightLabel: '30%',
    ),
    _ComponentMeta(
      key: 'expense_control',
      title: 'Expense Control',
      description: 'Expenses as % of income. Lower ratio keeps budgets in check.',
      icon: Icons.remove_circle_outline,
      color: Color(0xFFFF9800),
      weightLabel: '20%',
    ),
    _ComponentMeta(
      key: 'emergency_fund',
      title: 'Emergency Fund',
      description: 'Months of essential expenses covered by liquid savings.',
      icon: Icons.health_and_safety_outlined,
      color: Color(0xFF4DD0E1),
      weightLabel: '20%',
    ),
    _ComponentMeta(
      key: 'debt_health',
      title: 'Debt Health',
      description: 'EMI burden as % of income. Lower keeps cash flow flexible.',
      icon: Icons.account_balance_wallet_outlined,
      color: Color(0xFFFF6F61),
      weightLabel: '15%',
    ),
    _ComponentMeta(
      key: 'income_stability',
      title: 'Income Stability',
      description: 'Variance in income over 6 months. Steady inflows = better.',
      icon: Icons.auto_graph,
      color: Color(0xFFAB89FF),
      weightLabel: '15%',
    ),
  ];

  @override
  void initState() {
    super.initState();
    _loadSummary();
  }

  Future<void> _loadSummary() async {
    try {
      final summary = await _apiService.getDashboardSummary(userId: _userId);
      if (!mounted) return;
      setState(() {
        _summary = summary;
        _isLoading = false;
        _error = null;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = 'Failed to load dashboard: $e';
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: DashboardScreen.bgColor,
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 10.0),
          child: _buildBodyContent(),
        ),
      ),
    );
  }

  Widget _buildBodyContent() {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(color: DashboardScreen.accentGreen),
      );
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              _error!,
              style: const TextStyle(color: DashboardScreen.textPrimary),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 16),
            ElevatedButton(
              onPressed: () {
                setState(() {
                  _isLoading = true;
                  _error = null;
                });
                _loadSummary();
              },
              child: const Text('Retry'),
            ),
          ],
        ),
      );
    }

    return SingleChildScrollView(
      physics: const BouncingScrollPhysics(),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          _buildHeader(context),
          const SizedBox(height: 24),
          _buildHeroBanner(),
          const SizedBox(height: 32),
          _buildStabilityScore(),
          const SizedBox(height: 30),
          _buildIncomeSavingsRow(),
          const SizedBox(height: 20),
          _buildBudgetStatus(context),
          const SizedBox(height: 30),
          _buildAlertsSection(),
          const SizedBox(height: 20),
        ],
      ),
    );

  }

  Widget _buildHeroBanner() {
    final streak = _summary?.streakMetrics;
    if (streak == null) {
      return SizedBox.shrink();
    }
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.symmetric(horizontal: 0),
      padding: const EdgeInsets.symmetric(vertical: 24, horizontal: 24),
      decoration: BoxDecoration(
        color: DashboardScreen.accentGreen.withOpacity(0.12),
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          Text(
            'Momentum Streak',
            style: TextStyle(
              color: DashboardScreen.accentGreen,
              fontSize: 22,
              fontWeight: FontWeight.bold,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [
              _heroStat('Streak', '${streak.streakDays} days', Icons.flash_on, DashboardScreen.accentGreen),
              _heroStat('Consistency', '${streak.consistencyPct.toStringAsFixed(0)}%', Icons.timeline, DashboardScreen.textSecondary),
              _heroStat('Score', '${streak.score.toStringAsFixed(0)} / 100', Icons.emoji_events, DashboardScreen.textPrimary),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            'Last ${streak.streakMonths} months streak · ${streak.missedMonths} missed',
            style: TextStyle(
              color: DashboardScreen.textSecondary,
              fontSize: 13,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }

  Widget _heroStat(String label, String value, IconData icon, Color color) {
    return Column(
      children: [
        Container(
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            color: color.withOpacity(0.18),
            shape: BoxShape.circle,
          ),
          child: Icon(icon, color: color, size: 22),
        ),
        const SizedBox(height: 6),
        Text(
          value,
          style: TextStyle(
            color: DashboardScreen.textDark,
            fontSize: 16,
            fontWeight: FontWeight.bold,
          ),
        ),
        Text(
          label,
          style: TextStyle(
            color: DashboardScreen.textSecondary,
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget _buildHeader(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Expanded(
          child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Row(
              children: [
                Text(
                  'Hi, Rahul',
                  style: TextStyle(
                    color: DashboardScreen.textPrimary,
                    fontSize: 28,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                SizedBox(width: 8),
                Text('👋', style: TextStyle(fontSize: 24)),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              'Welcome back to Stocki',
              style: TextStyle(
                color: DashboardScreen.textSecondary,
                fontSize: 16,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
          ),
        ),
        GestureDetector(
          onTap: () => context.go('/profile'),
          child: Column(
            children: [
              Container(
                height: 54,
                width: 54,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: DashboardScreen.accentGreen.withOpacity(0.25),
                  border: Border.all(
                    color: DashboardScreen.accentGreen.withOpacity(0.8),
                    width: 2,
                  ),
                ),
                child: const Center(
                  child: Text(
                    'R',
                    style: TextStyle(
                      color: Color(0xFF0F262B),
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Profile',
                style: TextStyle(
                  color: DashboardScreen.textSecondary,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildStabilityScore() {
    final stability = _summary?.financialStability;
    final metrics = stability?.metrics;
    final score = stability?.score ?? 0.0;
    final displayScore = score.isFinite ? score.toStringAsFixed(0) : '--';
    final progressValue = score.isFinite ? (score / 100).clamp(0.0, 1.0) : 0.0;
    final label = (stability?.label ?? 'Need more data').toUpperCase();

    return Column(
      children: [
        GestureDetector(
          behavior: HitTestBehavior.opaque,
          onTap: stability != null ? _showStabilityBreakdown : null,
          child: SizedBox(
            height: 220,
            width: 220,
            child: Stack(
              fit: StackFit.expand,
              alignment: Alignment.center,
              children: [
                Container(
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    boxShadow: [
                      BoxShadow(
                        color: DashboardScreen.accentGreen.withOpacity(0.15),
                        blurRadius: 50,
                        spreadRadius: 10,
                      ),
                    ],
                  ),
                ),
                CircularProgressIndicator(
                  value: progressValue,
                  strokeWidth: 16,
                  backgroundColor: Colors.white.withOpacity(0.05),
                  color: DashboardScreen.accentGreen,
                  strokeCap: StrokeCap.round,
                ),
                Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      displayScore,
                      style: const TextStyle(
                        color: DashboardScreen.textPrimary,
                        fontSize: 64,
                        fontWeight: FontWeight.w800,
                        height: 1.1,
                      ),
                    ),
                    const SizedBox(height: 8),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                      decoration: BoxDecoration(
                        color: DashboardScreen.accentGreen.withOpacity(0.2),
                        borderRadius: BorderRadius.circular(20),
                        border: Border.all(color: DashboardScreen.accentGreen.withOpacity(0.5)),
                      ),
                      child: Text(
                        label,
                        style: const TextStyle(
                          color: DashboardScreen.accentGreen,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                          letterSpacing: 1.0,
                        ),
                      ),
                    ),
                    if (stability != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 8.0),
                        child: Text(
                          'Tap to view breakdown',
                          style: TextStyle(
                            color: DashboardScreen.textSecondary.withOpacity(0.8),
                            fontSize: 12,
                          ),
                        ),
                      ),
                  ],
                ),
              ],
            ),
          ),
        ),
        const SizedBox(height: 24),
        const Text(
          'Financial Stability Score',
          style: TextStyle(
            color: DashboardScreen.textSecondary,
            fontSize: 18,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget _buildIncomeSavingsRow() {
    final summary = _summary;
    final income = summary?.incomeVsExpense.income ?? 0.0;
    final expense = summary?.incomeVsExpense.expense ?? 0.0;
    final net = summary?.incomeVsExpense.net ?? 0.0;
    final savingsRate = summary?.savingsRate ?? 0.0;

    return Row(
      children: [
        Expanded(
          child: _buildInfoCard(
            title: 'Income vs Exp',
            amount: _formatCurrency(income),
            subtitle: 'Expenses ${_formatCurrency(expense)}',
            isPositive: income >= expense,
            iconData: Icons.swap_vert,
            iconColor: Colors.tealAccent,
          ),
        ),
        const SizedBox(width: 16),
        Expanded(
          child: _buildInfoCard(
            title: 'Savings Rate',
            amount: _formatPercent(savingsRate),
            subtitle: net >= 0
                ? 'Net ${_formatCurrency(net)}'
                : 'Deficit ${_formatCurrency(net.abs())}',
            isPositive: savingsRate >= 0,
            iconData: Icons.trending_up,
            iconColor: DashboardScreen.accentGreen,
          ),
        ),
      ],
    );
  }

  Widget _buildInfoCard({
    required String title,
    required String amount,
    required String subtitle,
    required bool isPositive,
    required IconData iconData,
    required Color iconColor,
  }) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: DashboardScreen.whiteCardColor,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: iconColor.withOpacity(0.1),
              shape: BoxShape.circle,
            ),
            child: Icon(iconData, color: iconColor, size: 24),
          ),
          const SizedBox(height: 24),
          Text(
            title,
            style: const TextStyle(
              color: Color(0xFF6B7E82),
              fontSize: 14,
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            amount,
            style: const TextStyle(
              color: DashboardScreen.textDark,
              fontSize: 26,
              fontWeight: FontWeight.w800,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            subtitle,
            style: TextStyle(
              color: isPositive ? DashboardScreen.accentGreen : Colors.redAccent,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildBudgetStatus(BuildContext context) {
    final budgets = _summary?.budgets ?? [];
    final visibleBudgets = budgets.take(4).toList();

    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: DashboardScreen.whiteCardColor,
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text(
                'Budget Status',
                style: TextStyle(
                  color: DashboardScreen.textDark,
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                ),
              ),
              TextButton(
                style: TextButton.styleFrom(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                  foregroundColor: DashboardScreen.accentGreen,
                  textStyle: const TextStyle(fontWeight: FontWeight.bold),
                ),
                onPressed: () => context.go('/expenses'),
                child: const Text('View All'),
              ),
            ],
          ),
          const SizedBox(height: 24),
          if (visibleBudgets.isEmpty)
            const Text(
              'No active budgets found. Create one to start tracking.',
              style: TextStyle(
                color: Color(0xFF6B7E82),
                fontSize: 14,
              ),
            )
          else
            ...visibleBudgets.map((budget) {
              return Padding(
                padding: const EdgeInsets.only(bottom: 20),
                child: _buildBudgetProgressRow(budget),
              );
            }),
        ],
      ),
    );
  }

  Widget _buildBudgetProgressRow(BudgetStatusItem budget) {
    final spentLabel = '${_formatCurrency(budget.spentAmount)} / ${_formatCurrency(budget.limitAmount)}';
    final progress = budget.limitAmount <= 0 ? 0.0 : budget.spentAmount / budget.limitAmount;
    Color barColor;
    if (progress <= 0.9) {
      barColor = DashboardScreen.accentGreen;
    } else if (progress <= 1.0) {
      barColor = Colors.orangeAccent;
    } else {
      barColor = Colors.redAccent;
    }

    return Column(
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              budget.category,
              style: const TextStyle(
                color: DashboardScreen.textDark,
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            Text(
              spentLabel,
              style: const TextStyle(
                color: Color(0xFF6B7E82),
                fontSize: 14,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        Align(
          alignment: Alignment.centerLeft,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
            decoration: BoxDecoration(
              color: Colors.grey.withOpacity(0.15),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
              budget.period.toUpperCase(),
              style: const TextStyle(
                color: Color(0xFF6B7E82),
                fontSize: 11,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
        ),
        const SizedBox(height: 10),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: LinearProgressIndicator(
            value: progress.clamp(0.0, 1.0),
            minHeight: 8,
            backgroundColor: Colors.grey.withOpacity(0.2),
            valueColor: AlwaysStoppedAnimation<Color>(barColor),
          ),
        ),
      ],
    );
  }

  Widget _buildAlertsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Alerts',
          style: TextStyle(
            color: DashboardScreen.textPrimary,
            fontSize: 22,
            fontWeight: FontWeight.bold,
          ),
        ),
        const SizedBox(height: 16),
        _buildAlertCard(
          iconData: Icons.error_outline,
          iconColor: Colors.redAccent,
          title: 'Overspending Alert',
          message: 'Shopping exceeded budget by ₹800',
        ),
        const SizedBox(height: 12),
        _buildAlertCard(
          iconData: Icons.warning_amber_rounded,
          iconColor: Colors.orangeAccent,
          title: 'Burn Rate Warning',
          message: 'At current pace, savings will drop 12% this month',
        ),
      ],
    );
  }

  Widget _buildAlertCard({
    required IconData iconData,
    required Color iconColor,
    required String title,
    required String message,
  }) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: Container(
        color: DashboardScreen.darkCardColor,
        child: IntrinsicHeight(
          child: Row(
            children: [
              Container(width: 4, color: iconColor),
              Padding(
                padding: const EdgeInsets.all(16.0),
                child: Icon(iconData, color: iconColor, size: 24),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 16.0).copyWith(right: 16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        title,
                        style: const TextStyle(
                          color: DashboardScreen.textPrimary,
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        message,
                        style: const TextStyle(
                          color: DashboardScreen.textSecondary,
                          fontSize: 14,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
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

  String _formatPercent(double value) {
    if (value.isNaN || value.isInfinite) return '--';
    return '${value.toStringAsFixed(1)}%';
  }

  String _formatMonths(double value) {
    if (value.isNaN || value.isInfinite) return '--';
    final decimals = value >= 10 ? 0 : 1;
    return '${value.toStringAsFixed(decimals)} mo';
  }

  void _showStabilityBreakdown() {
    final stability = _summary?.financialStability;
    if (stability == null) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('No stability data available yet.')),
        );
      }
      return;
    }

    showModalBottomSheet<void>(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (ctx) {
        return DraggableScrollableSheet(
          initialChildSize: 0.65,
          minChildSize: 0.4,
          maxChildSize: 0.9,
          builder: (_, controller) {
            return Container(
              decoration: const BoxDecoration(
                color: DashboardScreen.bgColor,
                borderRadius: BorderRadius.vertical(top: Radius.circular(28)),
              ),
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
              child: Column(
                children: [
                  Container(
                    width: 48,
                    height: 5,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.2),
                      borderRadius: BorderRadius.circular(20),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Financial Stability Breakdown',
                    style: const TextStyle(
                      color: DashboardScreen.textPrimary,
                      fontSize: 20,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Score ${stability.score.toStringAsFixed(1)} · ${stability.label}',
                    style: const TextStyle(
                      color: DashboardScreen.textSecondary,
                      fontSize: 14,
                    ),
                  ),
                  const SizedBox(height: 12),
                  Expanded(
                    child: ListView.builder(
                      controller: controller,
                      padding: EdgeInsets.zero,
                      itemCount: _componentMeta.length,
                      itemBuilder: (_, index) {
                        final meta = _componentMeta[index];
                        final component = stability.components[meta.key];
                        return _buildComponentRow(meta, component, stability);
                      },
                    ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  Widget _buildComponentRow(
    _ComponentMeta meta,
    ComponentScore? component,
    FinancialStability stability,
  ) {
    final score = component?.score ?? 0.0;
    final progress = (score / 100).clamp(0.0, 1.0);
    final valueLabel = _componentValueLabel(meta.key, stability);

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: DashboardScreen.darkCardColor.withOpacity(0.7),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: meta.color.withOpacity(0.18),
                ),
                child: Icon(meta.icon, color: meta.color, size: 22),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      meta.title,
                      style: const TextStyle(
                        color: DashboardScreen.textPrimary,
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    Text(
                      meta.description,
                      style: const TextStyle(
                        color: DashboardScreen.textSecondary,
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: Colors.white12),
                ),
                child: Text(
                  meta.weightLabel,
                  style: const TextStyle(
                    color: DashboardScreen.textSecondary,
                    fontSize: 12,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                valueLabel,
                style: const TextStyle(
                  color: DashboardScreen.textPrimary,
                  fontSize: 14,
                  fontWeight: FontWeight.w600,
                ),
              ),
              Text(
                '${score.toStringAsFixed(0)} / 100',
                style: const TextStyle(
                  color: DashboardScreen.textSecondary,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 8,
              backgroundColor: Colors.white.withOpacity(0.08),
              valueColor: AlwaysStoppedAnimation<Color>(meta.color),
            ),
          ),
        ],
      ),
    );
  }

  String _componentValueLabel(String key, FinancialStability stability) {
    final metrics = stability.metrics;
    switch (key) {
      case 'savings_rate':
        return '${_formatPercent(metrics.savingsRatePct)} saved';
      case 'expense_control':
        return '${_formatPercent(metrics.expenseRatioPct)} spend/income';
      case 'emergency_fund':
        return '${_formatMonths(metrics.emergencyMonths)} runway';
      case 'debt_health':
        return '${_formatPercent(metrics.emiRatioPct)} EMI load';
      case 'income_stability':
        return '${_formatPercent(metrics.incomeCvPct)} variance';
      default:
        return '${stability.score.toStringAsFixed(1)} pts';
    }
  }
}