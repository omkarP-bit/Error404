import 'dart:convert';

class Goal {
  final int? id;
  final int userId;
  final String name;
  final String type;
  final double targetAmount;
  final double savedAmount;
  final double monthlyContribution;
  final DateTime? deadline;
  final int priority;
  final String status;
  final double? feasibilityScore;
  final String? feasibilityNote;
  final DateTime? createdAt;

  Goal({
    this.id,
    required this.userId,
    required this.name,
    required this.type,
    required this.targetAmount,
    this.savedAmount = 0.0,
    required this.monthlyContribution,
    this.deadline,
    required this.priority,
    required this.status,
    this.feasibilityScore,
    this.feasibilityNote,
    this.createdAt,
  });

  Map<String, dynamic> toMap() {
    return {
      'id': id,
      'user_id': userId,
      'name': name,
      'type': type,
      'target_amount': targetAmount,
      'saved_amount': savedAmount,
      'monthly_contribution': monthlyContribution,
      'deadline': deadline?.toIso8601String(),
      'priority': priority,
      'status': status,
      'feasibility_score': feasibilityScore,
      'feasibility_note': feasibilityNote,
      'created_at': createdAt?.toIso8601String() ?? DateTime.now().toIso8601String(),
    };
  }

  factory Goal.fromMap(Map<String, dynamic> map) {
    return Goal(
      id: map['id'],
      userId: map['user_id'],
      name: map['name'],
      type: map['type'],
      targetAmount: (map['target_amount'] as num).toDouble(),
      savedAmount: (map['saved_amount'] as num).toDouble(),
      monthlyContribution: (map['monthly_contribution'] as num).toDouble(),
      deadline: map['deadline'] != null ? DateTime.parse(map['deadline']) : null,
      priority: map['priority'],
      status: map['status'],
      feasibilityScore: map['feasibility_score'] != null ? (map['feasibility_score'] as num).toDouble() : null,
      feasibilityNote: map['feasibility_note'],
      createdAt: map['created_at'] != null ? DateTime.parse(map['created_at']) : null,
    );
  }

  String toJson() => json.encode(toMap());

  factory Goal.fromJson(String source) => Goal.fromMap(json.decode(source));
}
