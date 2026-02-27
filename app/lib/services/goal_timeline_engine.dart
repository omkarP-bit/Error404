import 'dart:math';

class GoalTimelineResult {
  final int monthsToTarget;
  final int? monthsToDeadline;
  final int? deltaMonths; // monthsToTarget - monthsToDeadline (positive => late)
  final bool hasDeadline;

  GoalTimelineResult({
    required this.monthsToTarget,
    this.monthsToDeadline,
    this.deltaMonths,
    required this.hasDeadline,
  });
}

class GoalTimelineEngine {
  GoalTimelineResult simulate({
    required double targetAmount,
    required double savedAmount,
    required double monthlyContribution,
    required DateTime? deadline,
    required double annualExpectedReturn,
  }) {
    int monthsToTarget = 0;
    
    if (savedAmount >= targetAmount) {
      monthsToTarget = 0;
    } else if (monthlyContribution <= 0) {
      monthsToTarget = 999;
    } else {
      double monthlyReturn = annualExpectedReturn / 12;
      double balance = savedAmount;
      int months = 0;
      while (balance < targetAmount && months < 1200) {
        balance = balance * (1 + monthlyReturn);
        balance += monthlyContribution;
        months += 1;
      }
      monthsToTarget = months;
    }

    int? monthsToDeadline;
    int? deltaMonths;
    bool hasDeadline = deadline != null;

    if (hasDeadline) {
      final now = DateTime.now();
      monthsToDeadline = max(0, (deadline!.year - now.year) * 12 + deadline.month - now.month);
      deltaMonths = monthsToTarget == 999 ? 999 : monthsToTarget - monthsToDeadline;
    }

    return GoalTimelineResult(
      monthsToTarget: monthsToTarget,
      monthsToDeadline: monthsToDeadline,
      deltaMonths: deltaMonths,
      hasDeadline: hasDeadline,
    );
  }

  static double expectedReturnForGoal({
    required String goalType,
    required int? monthsToDeadline,
  }) {
    switch (goalType) {
      case 'emergency_fund':
        return 0.06;
      case 'short_term':
        return 0.08;
      case 'long_term':
        return 0.12;
      case 'retirement':
        return 0.13;
      default:
        if (monthsToDeadline != null && monthsToDeadline <= 36) return 0.08;
        if (monthsToDeadline != null && monthsToDeadline <= 84) return 0.11;
        return 0.12;
    }
  }
}
