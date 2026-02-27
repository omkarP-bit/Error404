import 'dart:convert';
import 'dart:math';
import 'package:flutter/services.dart';
import 'package:sqflite/sqflite.dart';
import 'local_goals_db.dart';
import 'local_user_settings.dart';
import '../models/goal.dart';

class GoalProbabilityService {
  static final GoalProbabilityService _instance = GoalProbabilityService._internal();
  factory GoalProbabilityService() => _instance;
  GoalProbabilityService._internal();

  Map<String, dynamic>? _modelData;
  final LocalGoalsDB _dbService = LocalGoalsDB();
  final LocalUserSettings _userSettings = LocalUserSettings();

  Future<void> init() async {
    if (_modelData != null) return;
    try {
      final jsonString = await rootBundle.loadString('assets/models/goal_feasibility.json');
      _modelData = json.decode(jsonString);
    } catch (e) {
      print('⚠️ Failed to load ML model: $e');
    }
  }

  Future<void> ensureFeasibilityComputed(Goal goal) async {
    if (goal.feasibilityScore != null) return;
    await computeAndSaveFeasibility(goal);
  }

  Future<void> computeAndSaveFeasibility(Goal goal) async {
    await init();
    if (_modelData == null || goal.id == null) return;

    final features = await _buildFeatureVector(goal);

    // Scaling & Inference
    final List<dynamic> featureNames = _modelData!['features'];
    final List<dynamic> means = _modelData!['scaler']['mean'];
    final List<dynamic> scales = _modelData!['scaler']['scale'];
    final Map<String, dynamic> weights = _modelData!['weights'];
    final double bias = _modelData!['bias'].toDouble();

    double logit = bias;
    List<double> featureValues = [];
    
    // Detailed log of features contributing most positively/negatively
    List<Map<String, dynamic>> impact = [];

    for (int i = 0; i < featureNames.length; i++) {
      final name = featureNames[i] as String;
      final rawValue = features[name] ?? 0.0;
      final mean = (means[i] as num).toDouble();
      final scale = (scales[i] as num).toDouble();
      final weight = (weights[name] as num).toDouble();

      final scaledVal = scale == 0 ? 0.0 : (rawValue - mean) / scale;
      final term = weight * scaledVal;
      logit += term;

      featureValues.add(rawValue);
      impact.add({'name': name, 'impact': term});
    }

    final prob = 1.0 / (1.0 + exp(-logit));
    
    // Sort to find biggest drivers for the note
    impact.sort((a, b) => (b['impact'] as double).compareTo(a['impact'] as double));
    
    print('==============================');
    print('ML Goal Probability Inference:');
    print('Goal: ${goal.name}');
    for (int i = 0; i < featureNames.length; i++) {
      print(' - ${featureNames[i]}: ${featureValues[i].toStringAsFixed(4)}');
    }
    print('Raw Logit: $logit');
    print('Probability: ${(prob * 100).toStringAsFixed(2)}%');
    print('Top positive driver: ${impact.first['name']}');
    print('Top negative driver: ${impact.last['name']}');
    print('==============================');

    String note = _generateHumanNote(prob, impact.first['name'] as String, impact.last['name'] as String);

    await _dbService.updateGoalFeasibility(goal.id!, prob, note);
  }

  String _generateHumanNote(double prob, String topPos, String topNeg) {
    if (prob > 0.8) {
      if (topPos.contains('streak') || topPos.contains('consistency')) return "Excellent saving consistency puts this goal safely on track.";
      if (topPos.contains('surplus') || topPos.contains('income')) return "Your high financial capacity securely backs this goal.";
      return "On track to hit this target comfortably.";
    } else if (prob > 0.5) {
      if (topNeg.contains('volatility') || topNeg.contains('anomaly')) return "Likely achievable, though unexpected expenses might shift timelines.";
      if (topNeg.contains('time') || topNeg.contains('left')) return "Looks achievable, though time is tightening.";
      return "Feasible on current trajectory.";
    } else {
      if (topNeg.contains('surplus') || topNeg.contains('ratio')) return "Current saving rate might not meet the required pace.";
      if (topNeg.contains('drift') || topNeg.contains('discretionary')) return "Increasing discretionary spend is reducing feasibility.";
      return "Requires a pace adjustment to stay on track.";
    }
  }

  Future<Map<String, double>> _buildFeatureVector(Goal goal) async {
    final dbClient = await _dbService.db;
    final int userId = 1;

    // A. Goal Features
    final target = goal.targetAmount;
    final current = goal.savedAmount;
    double remaining = max(target - current, 0.0);

    double monthsLeft = 12.0;
    if (goal.deadline != null) {
      final days = goal.deadline!.difference(DateTime.now()).inDays;
      monthsLeft = max(days / 30.44, 0.01);
    }
    double monthlyRequired = monthsLeft > 0 ? remaining / monthsLeft : remaining;
    
    // B. Capacity & User Setup
    double monthlyIncome = 0.0;
    try {
      final userRes = await dbClient.query('users', where: 'user_id = ?', whereArgs: [userId]);
      if (userRes.isNotEmpty) {
        monthlyIncome = (userRes.first['monthly_income'] as num?)?.toDouble() ?? 0.0;
      }
    } catch (_) {} // table might not exist

    double avgSurplus = await _userSettings.getMonthlySurplus();
    if (avgSurplus == 0.0) {
      avgSurplus = monthlyIncome * 0.2; // Fallback rule for new users
    }
    
    double safeSurplus = avgSurplus * 0.85;

    // C. Behaviour Defaults (assuming tables like transactions/budget_profiles are missing in this environment)
    int anomalyCount3m = 0;
    double expenseVolatility = avgSurplus * 0.1;
    double avgMonthlyExpenses = monthlyIncome > 0 ? monthlyIncome - avgSurplus : 0.0;
    if (avgMonthlyExpenses < 0) avgMonthlyExpenses = 0.0;
    double debitSum3m = avgMonthlyExpenses * 3;
    double debitSum6m = avgMonthlyExpenses * 6;
    
    double shoppingSlope = 0.0;
    double diningSlope = 0.0;
    double entertainmentSlope = 0.0;
    double contributionStreak = 3.0; // Assume somewhat consistent
    int missedSavingMonths = 0;
    double behavioralConsistency = 0.8;
    double currBalance = current * 1.5;

    try {
      final txnsCount = Sqflite.firstIntValue(await dbClient.rawQuery('SELECT COUNT(*) FROM transactions'));
      if (txnsCount != null && txnsCount > 0) {
        // Just empty blocks - if table actually existed we'd query it. 
        // For our offline prototype, we rely on the graceful fallback.
      }
    } catch (_) {}

    try {
      final act = await dbClient.query('savings_activity', orderBy: 'month_key DESC', limit: 12);
      if (act.isNotEmpty) {
        int streak = 0;
        int missed = 0;
        for (var row in act) {
          if (row['missed'] == 1) missed++;
          if (row['contributed'] == 1 && missed == 0) streak++;
        }
        contributionStreak = streak.toDouble();
        missedSavingMonths = missed;
      }
    } catch (_) {}

    return {
      "log_target_amount":        log(target + 1),
      "log_remaining_amount":     log(remaining + 1),
      "months_left":              monthsLeft,
      "monthly_required":         monthlyRequired,
      "progress_pct":             target > 0 ? current / target : 0.0,
      "monthly_income":           monthlyIncome,
      "avg_monthly_surplus":      avgSurplus,
      "expense_volatility":       expenseVolatility,
      "current_balance":          currBalance,
      "safe_surplus":             safeSurplus,
      "savings_rate":             monthlyIncome > 0 ? safeSurplus / monthlyIncome : 0.0,
      "feasibility_ratio":        monthlyRequired > 0 ? safeSurplus / monthlyRequired : safeSurplus,
      "avg_monthly_expenses":     avgMonthlyExpenses,
      "expense_volatility_ratio": avgMonthlyExpenses > 0 ? expenseVolatility / avgMonthlyExpenses : 0.0,
      "anomaly_count_3m":         anomalyCount3m.toDouble(),
      "recurring_expense_ratio":  0.4,
      "discretionary_ratio":      0.3,
      "txn_frequency":            20.0, // standard user proxy
      "high_value_txn_count":     1.0,
      "dining_slope":             diningSlope,
      "shopping_slope":           shoppingSlope,
      "entertainment_slope":      entertainmentSlope,
      "contribution_streak":      contributionStreak,
      "missed_saving_months":     missedSavingMonths.toDouble(),
      "behavioral_consistency":   behavioralConsistency,
      "health_score":             0.8,
      "debit_ratio_3m_6m":        debitSum6m > 0 ? debitSum3m / (debitSum6m / 2) : 1.0,
      "income_stability":         1.0, // assumption mapping
    };
  }
}
