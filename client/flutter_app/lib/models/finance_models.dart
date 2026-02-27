class Budget {
  final int budgetId;
  final int userId;
  final String category;
  final double limitAmount;
  final double spentAmount;
  final String period;
  final bool isActive;

  Budget({
    required this.budgetId,
    required this.userId,
    required this.category,
    required this.limitAmount,
    required this.spentAmount,
    required this.period,
    required this.isActive,
  });

  factory Budget.fromJson(Map<String, dynamic> json) {
    return Budget(
      budgetId: json['budget_id'],
      userId: json['user_id'],
      category: json['category'],
      limitAmount: double.parse(json['limit_amount'].toString()),
      spentAmount: double.parse(json['spent_amount'].toString()),
      period: json['period'],
      isActive: json['is_active'],
    );
  }

  double get percentageUsed => (spentAmount / limitAmount * 100).clamp(0, 100);
  double get remaining => (limitAmount - spentAmount).clamp(0, limitAmount);
}

class Goal {
  final int goalId;
  final int userId;
  final String goalName;
  final double targetAmount;
  final double currentAmount;
  final DateTime? deadline;
  final String status;
  final double? feasibilityScore;

  Goal({
    required this.goalId,
    required this.userId,
    required this.goalName,
    required this.targetAmount,
    required this.currentAmount,
    this.deadline,
    required this.status,
    this.feasibilityScore,
  });

  factory Goal.fromJson(Map<String, dynamic> json) {
    return Goal(
      goalId: json['goal_id'],
      userId: json['user_id'],
      goalName: json['goal_name'],
      targetAmount: double.parse(json['target_amount'].toString()),
      currentAmount: double.parse(json['current_amount'].toString()),
      deadline: json['deadline'] != null ? DateTime.parse(json['deadline']) : null,
      status: json['status'],
      feasibilityScore: json['feasibility_score'] != null 
          ? double.parse(json['feasibility_score'].toString()) 
          : null,
    );
  }

  double get progress => (currentAmount / targetAmount * 100).clamp(0, 100);
}

class Alert {
  final int alertId;
  final int userId;
  final String alertType;
  final String severity;
  final String status;
  final String message;
  final DateTime createdAt;

  Alert({
    required this.alertId,
    required this.userId,
    required this.alertType,
    required this.severity,
    required this.status,
    required this.message,
    required this.createdAt,
  });

  factory Alert.fromJson(Map<String, dynamic> json) {
    return Alert(
      alertId: json['alert_id'],
      userId: json['user_id'],
      alertType: json['alert_type'],
      severity: json['severity'],
      status: json['status'],
      message: json['message'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }
}
