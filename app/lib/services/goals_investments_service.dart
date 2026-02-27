import 'dart:math';
import 'package:flutter/material.dart';
import 'package:supabase_flutter/supabase_flutter.dart';
import '../models/goal_vm.dart';
import '../models/investment_overview_vm.dart';

class GoalsInvestmentsService {
  final _supabase = Supabase.instance.client;

  Future<int> _getCurrentUserId() async {
    // TEMPORARY BYPASS: Grab the first user in the DB
    final response = await _supabase
        .from('users')
        .select('user_id')
        .limit(1)
        .maybeSingle();

    if (response == null) {
      // IF THE DATABASE IS COMPLETELY EMPTY, RETURN A DUMMY ID SO IT DOESN'T CRASH
      return 1; // Assuming '1' will at least load an empty profile cleanly
    }
    
    return response['user_id'] as int;
  }

  Future<List<GoalVM>> _fetchGoalsVM(int userId) async {
    final response = await _supabase
        .from('goals')
        .select()
        .eq('user_id', userId)
        .eq('status', 'active')
        .order('priority', ascending: true)
        .order('created_at', ascending: true);

    final List<GoalVM> goals = [];
    final now = DateTime.now();
    
    const Color accentGreen = Color(0xFF5DF22A);

    for (var row in response) {
      final targetAmount = (row['target_amount'] ?? 0).toDouble();
      final savedAmount = (row['saved_amount'] ?? 0).toDouble();
      final monthlyContrib = (row['monthly_contribution'] ?? 0).toDouble();
      final priority = row['priority'] as int? ?? 99;
      final deadlineStr = row['deadline'] as String?;
      DateTime? deadline;
      if (deadlineStr != null) {
        deadline = DateTime.tryParse(deadlineStr);
      }

      double progress = targetAmount > 0 ? (savedAmount / targetAmount).clamp(0.0, 1.0) : 0.0;
      int? monthsLeft;
      double monthlyRequired = 0.0;
      String statusLabel = "ON TRACK";
      Color statusColor = accentGreen;

      if (deadline != null) {
        int diffMonths = (deadline.year - now.year) * 12 + deadline.month - now.month;
        monthsLeft = max(0, diffMonths);
        double remaining = max(0, targetAmount - savedAmount);
        monthlyRequired = monthsLeft > 0 ? remaining / monthsLeft : remaining;

        double feasibilityRatio = monthlyRequired > 0 ? (monthlyContrib > 0 ? monthlyContrib : 0) / monthlyRequired : 999.0;
        
        if (feasibilityRatio >= 1.2) {
          statusLabel = "ON TRACK";
          statusColor = accentGreen;
        } else if (feasibilityRatio >= 0.9) {
          statusLabel = "TIGHT";
          statusColor = Colors.orange;
        } else {
          statusLabel = "BEHIND";
          statusColor = Colors.redAccent;
        }
      } else {
        monthlyRequired = monthlyContrib;
        if (monthlyContrib > 0) {
          statusLabel = "ON TRACK";
          statusColor = accentGreen;
        } else {
          statusLabel = "TIGHT";
          statusColor = Colors.orange;
        }
      }

      final goalType = row['goal_type'] as String? ?? 'custom';
      IconData icon;
      Color iconColor;
      Color iconBgColor;

      switch (goalType) {
        case 'emergency_fund':
          icon = Icons.health_and_safety;
          iconColor = Colors.teal;
          iconBgColor = const Color(0xFFE0F2F1);
          break;
        case 'short_term':
          icon = Icons.flight_takeoff;
          iconColor = Colors.orange;
          iconBgColor = const Color(0xFFFFF3E0);
          break;
        case 'long_term':
          icon = Icons.home;
          iconColor = Colors.blue;
          iconBgColor = const Color(0xFFE3F2FD);
          break;
        case 'retirement':
          icon = Icons.savings;
          iconColor = Colors.purple;
          iconBgColor = const Color(0xFFF3E5F5);
          break;
        default:
          icon = Icons.track_changes;
          iconColor = Colors.teal;
          iconBgColor = const Color(0xFFE0F2F1);
      }

      goals.add(GoalVM(
        goalId: row['goal_id'] as int? ?? 0,
        goalName: row['goal_name'] as String? ?? 'Unnamed Goal',
        goalType: goalType,
        targetAmount: targetAmount,
        savedAmount: savedAmount,
        monthlyContribution: monthlyContrib,
        deadline: deadline,
        priority: priority,
        progress: progress,
        monthsLeft: monthsLeft,
        monthlyRequired: monthlyRequired,
        statusLabel: statusLabel,
        statusColor: statusColor,
        icon: icon,
        iconColor: iconColor,
        iconBgColor: iconBgColor,
      ));
    }
    return goals;
  }

  Future<Map<String, double>> _computeMonthlyIncomeExpense(int userId) async {
    final now = DateTime.now();
    final threeMonthsAgo = DateTime(now.year, now.month - 3, now.day).toIso8601String();

    final response = await _supabase
        .from('transactions')
        .select()
        .eq('user_id', userId)
        .gte('txn_timestamp', threeMonthsAgo);

    double totalIncome = 0;
    double totalExpense = 0;

    for (var row in response) {
      final amount = (row['amount'] ?? 0).toDouble();
      if (row['txn_type'] == 'credit') {
        totalIncome += amount;
      } else if (row['txn_type'] == 'debit') {
        totalExpense += amount;
      }
    }

    final avgIncome = totalIncome / 3.0;
    final avgExpense = totalExpense / 3.0;

    return {
      'income': avgIncome,
      'expense': avgExpense,
      'surplus': avgIncome - avgExpense,
    };
  }

  Future<Map<String, dynamic>> _emergencyGate(int userId) async {
    final response = await _supabase
        .from('goals')
        .select()
        .eq('user_id', userId)
        .eq('goal_type', 'emergency_fund')
        .eq('status', 'active')
        .limit(1)
        .maybeSingle();

    if (response == null) {
      return {'pass': false, 'reason': 'Add an emergency fund goal'};
    }

    final targetAmount = (response['target_amount'] ?? 0).toDouble();
    final savedAmount = (response['saved_amount'] ?? 0).toDouble();

    if (targetAmount > 0 && savedAmount >= 0.8 * targetAmount) {
      return {'pass': true, 'reason': 'Emergency fund funded'};
    } else {
      return {'pass': false, 'reason': 'Emergency fund below 80%'};
    }
  }

  Future<double> _computeSafeSipBudget(int userId, double avgMonthlySurplus) async {
    if (avgMonthlySurplus <= 0) return 0;

    final now = DateTime.now();
    final threeMonthsAgo = DateTime(now.year, now.month - 3, now.day).toIso8601String();
    
    final response = await _supabase
        .from('transactions')
        .select()
        .eq('user_id', userId)
        .eq('txn_type', 'debit')
        .gte('txn_timestamp', threeMonthsAgo);

    Map<int, double> monthlyExpenses = {};
    for (var row in response) {
      final dateStr = row['txn_timestamp'] as String;
      final date = DateTime.parse(dateStr);
      final monthKey = date.year * 12 + date.month;
      monthlyExpenses[monthKey] = (monthlyExpenses[monthKey] ?? 0) + (row['amount'] ?? 0).toDouble();
    }

    double cv = 0.0;
    if (monthlyExpenses.length >= 2) {
      final expenses = monthlyExpenses.values.toList();
      final mean = expenses.reduce((a, b) => a + b) / expenses.length;
      if (mean > 0) {
        final variance = expenses.map((e) => pow(e - mean, 2)).reduce((a, b) => a + b) / expenses.length;
        final stdDev = sqrt(variance);
        cv = stdDev / mean;
      }
    }

    double safetyFactor = 0.65;
    if (cv > 0.35) {
      safetyFactor = 0.45;
    } else if (cv > 0.20) {
      safetyFactor = 0.55;
    }

    double safeSip = avgMonthlySurplus * safetyFactor;
    return (safeSip / 100).round() * 100.0;
  }

  Map<String, int> _computeAllocation(String riskProfile, int? topGoalHorizonMonths, bool emergencyOk) {
    if (!emergencyOk) {
      return {
        "Equity (Index + Large Cap)": 0,
        "Debt/Liquid": 100,
        "Gold": 0,
        "International": 0,
      };
    }

    int equity = 55;
    int debt = 35;
    int gold = 10;
    int intl = 0;

    if (riskProfile == 'conservative') {
      equity = 15;
      debt = 75;
      gold = 10;
      intl = 0;
    } else if (riskProfile == 'aggressive') {
      equity = 75;
      debt = 15;
      gold = 5;
      intl = 5;
    }

    if (topGoalHorizonMonths != null) {
      if (topGoalHorizonMonths < 36) {
        if (equity > 20) {
          int delta = equity - 20;
          equity = 20;
          debt += delta;
        }
      } else if (topGoalHorizonMonths <= 84) {
        if (equity > 50) {
          int delta = equity - 50;
          equity = 50;
          debt += delta;
        }
      }
    }

    return {
      "Equity (Index + Large Cap)": equity,
      "Debt/Liquid": debt,
      "Gold": gold,
      "International": intl,
    };
  }

  Future<List<SavingsOpportunityVM>> _detectSavingsOpportunities(int userId) async {
    final now = DateTime.now();
    final threeMonthsAgo = DateTime(now.year, now.month - 3, now.day).toIso8601String();

    final response = await _supabase
        .from('transactions')
        .select()
        .eq('user_id', userId)
        .eq('txn_type', 'debit')
        .gte('txn_timestamp', threeMonthsAgo);

    Map<String, Map<int, double>> categoryMonthlySpend = {};
    Map<String, int> categoryRecurringCount = {};

    for (var row in response) {
      String category = row['category'] as String? ?? 'Other';
      bool isRecurring = row['is_recurring'] as bool? ?? false;
      double amount = (row['amount'] ?? 0).toDouble();
      
      final dateStr = row['txn_timestamp'] as String;
      final date = DateTime.parse(dateStr);
      final monthKey = date.year * 12 + date.month;

      if (!categoryMonthlySpend.containsKey(category)) {
        categoryMonthlySpend[category] = {};
      }
      categoryMonthlySpend[category]![monthKey] = (categoryMonthlySpend[category]![monthKey] ?? 0) + amount;
      
      if (isRecurring) {
        categoryRecurringCount[category] = (categoryRecurringCount[category] ?? 0) + 1;
      }
    }

    List<SavingsOpportunityVM> ops = [];
    final essentials = ["rent", "utilities", "groceries", "transport", "emi", "medical", "education"];

    for (var entry in categoryMonthlySpend.entries) {
      String category = entry.key;
      var monthsMap = entry.value;
      
      if (monthsMap.isEmpty) continue;

      double avgMonthlySpend = monthsMap.values.reduce((a, b) => a + b) / 3.0; // Assume 3 months
      
      var sortedMonths = monthsMap.keys.toList()..sort();
      double trend = 0.0;
      if (sortedMonths.length >= 2) {
        double month1 = monthsMap[sortedMonths.first] ?? 0;
        double month3 = monthsMap[sortedMonths.last] ?? 0;
        trend = (month3 - month1) / max(1, month1);
      }

      double suggestedCut = 0.0;
      String label = "";

      int recurringCount = categoryRecurringCount[category] ?? 0;
      if (recurringCount >= 6) { // ~2 per month for 3 months
        label = "Recurring: $category";
        suggestedCut = 0.15;
      } else if (trend > 0.25 && avgMonthlySpend > 1000) {
        label = "Category drift: $category";
        suggestedCut = 0.10;
      } else if (!essentials.contains(category.toLowerCase())) {
        label = "Reduce spend: $category";
        suggestedCut = 0.08;
      }

      if (suggestedCut > 0) {
        double unlockMonthly = avgMonthlySpend * suggestedCut;
        ops.add(SavingsOpportunityVM(
          label: label,
          monthlySpend: avgMonthlySpend,
          suggestedCut: unlockMonthly,
          unlockMonthly: unlockMonthly,
        ));
      }
    }

    ops.sort((a, b) => b.unlockMonthly.compareTo(a.unlockMonthly));
    return ops.take(3).toList();
  }

  int _simulateMonthsSavedForTopGoal(GoalVM? topGoal, double safeSipBudget, double unlockMonthly, int equityAllocation) {
    if (topGoal == null || safeSipBudget <= 0) return 0;

    double monthlyInvestBase = max(topGoal.monthlyContribution, safeSipBudget * 0.7);
    
    double expectedMonthlyReturn;
    if (equityAllocation <= 20) {
      expectedMonthlyReturn = 0.005;
    } else if (equityAllocation <= 50) {
      expectedMonthlyReturn = 0.0075;
    } else {
      expectedMonthlyReturn = 0.009;
    }

    int simulateMonths(double monthlyContributionUsed) {
      double bal = topGoal.savedAmount;
      int months = 0;
      while (bal < topGoal.targetAmount && months < 600) {
        bal = bal * (1 + expectedMonthlyReturn);
        bal += monthlyContributionUsed;
        months++;
      }
      return months;
    }

    int baseMonths = simulateMonths(monthlyInvestBase);
    int newMonths = simulateMonths(monthlyInvestBase + unlockMonthly);
    
    return max(0, baseMonths - newMonths);
  }

  Future<InvestmentOverviewVM> fetchGoalsAndInvestmentOverview() async {
    // TEMPORARY BYPASS: Return mock data instead of calling Supabase
    // This allows the app to function locally without a working Supabase connection.
    return InvestmentOverviewVM(
      investmentAllowed: true,
      gateReasons: ["Emergency fund funded"],
      monthlyIncome: 100000.0,
      avgMonthlyExpense: 40000.0,
      avgMonthlySurplus: 60000.0,
      safeSipBudget: 35000.0,
      riskProfile: 'aggressive',
      topGoalHorizonMonths: 24,
      allocation: {
        "Equity (Index + Large Cap)": 75,
        "Debt/Liquid": 15,
        "Gold": 5,
        "International": 5,
      },
      allocationAmounts: {
        "Equity (Index + Large Cap)": 26250.0,
        "Debt/Liquid": 5250.0,
        "Gold": 1750.0,
        "International": 1750.0,
      },
      expectedReturnText: "10–14% p.a.",
      probabilityText: "78% High",
      hiddenWealthTop3: [
        SavingsOpportunityVM(
          label: "Reduce spend: dining",
          monthlySpend: 5000.0,
          suggestedCut: 400.0,
          unlockMonthly: 400.0,
        )
      ],
      hiddenWealthUnlockMonthly: 400.0,
      monthsSavedForTopGoal: 3,
      goals: [],
    );
  }
}
