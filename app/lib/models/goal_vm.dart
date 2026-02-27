import 'package:flutter/material.dart';

class GoalVM {
  final int goalId;
  final String goalName;
  final String goalType;
  final double targetAmount;
  final double savedAmount;
  final double monthlyContribution;
  final DateTime? deadline;
  final int priority;
  final double progress;
  final int? monthsLeft;
  final double monthlyRequired;
  final String statusLabel; // "ON TRACK" | "TIGHT" | "BEHIND"
  final Color statusColor;
  final IconData icon;
  final Color iconColor;
  final Color iconBgColor;
  final double? feasibilityScore;
  final String? feasibilityNote;

  GoalVM({
    required this.goalId,
    required this.goalName,
    required this.goalType,
    required this.targetAmount,
    required this.savedAmount,
    required this.monthlyContribution,
    this.deadline,
    required this.priority,
    required this.progress,
    this.monthsLeft,
    required this.monthlyRequired,
    required this.statusLabel,
    required this.statusColor,
    required this.icon,
    required this.iconColor,
    required this.iconBgColor,
    this.feasibilityScore,
    this.feasibilityNote,
  });
}
