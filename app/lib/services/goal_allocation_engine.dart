import 'dart:math';
import '../models/goal.dart';

class AllocationResult {
  final Map<int, double> goalIdToMonthlyContribution;
  final double totalAllocated;
  final double unallocated;

  AllocationResult({
    required this.goalIdToMonthlyContribution,
    required this.totalAllocated,
    required this.unallocated,
  });
}

class GoalAllocationEngine {
  AllocationResult allocate({
    required double monthlySurplus,
    required List<Goal> activeGoals,
    Map<int, double>? customWeights,
  }) {
    if (monthlySurplus <= 0) {
      return AllocationResult(
        goalIdToMonthlyContribution: {},
        totalAllocated: 0,
        unallocated: 0,
      );
    }

    final validGoals = activeGoals.where((g) => g.status == 'active' && g.id != null).toList();
    if (validGoals.isEmpty) {
      return AllocationResult(
        goalIdToMonthlyContribution: {},
        totalAllocated: 0,
        unallocated: monthlySurplus,
      );
    }

    Map<int, double> allocation = {};
    double totalAllocated = 0.0;

    // 1) Identify emergency goal
    Goal? emergencyGoal;
    try {
      emergencyGoal = validGoals.firstWhere((g) => g.type == 'emergency_fund');
    } catch (_) {}

    double remainingSurplus = monthlySurplus;

    if (emergencyGoal != null) {
      bool emergencyIncomplete = false;
      if (emergencyGoal.targetAmount <= 0) {
        emergencyIncomplete = true;
      } else {
        emergencyIncomplete = emergencyGoal.savedAmount < (emergencyGoal.targetAmount * 0.80);
      }

      double allocateToEmergency = 0.0;

      if (emergencyIncomplete) {
        // Priority to emergency fund: 70% of monthlySurplus
        double emergencyShare = monthlySurplus * 0.70;
        double existing = emergencyGoal.monthlyContribution;
        allocateToEmergency = min(monthlySurplus, max(emergencyShare, existing));
      } else {
        // Emergency complete: set to 0 unless user had set it manually
        // If they manually set it, we could reuse it, but default to 0 for hackathon clarity.
        allocateToEmergency = emergencyGoal.monthlyContribution;
        if (allocateToEmergency > monthlySurplus) allocateToEmergency = monthlySurplus;
      }

      allocation[emergencyGoal.id!] = allocateToEmergency;
      totalAllocated += allocateToEmergency;
      remainingSurplus = max(0.0, monthlySurplus - totalAllocated);
    }

    // Distribute remainder across other goals
    List<Goal> high = [];
    List<Goal> medium = [];
    List<Goal> low = [];

    for (var g in validGoals) {
      if (g.type == 'emergency_fund') continue; // Handled

      if (g.priority == 1) {
        high.add(g);
      } else if (g.priority == 2) {
        medium.add(g);
      } else {
        low.add(g);
      }
    }

    if (remainingSurplus > 0) {
      // Priority weights
      double weightHigh = 0.50;
      double weightMedium = 0.30;
      double weightLow = 0.20;

      double activeWeightHigh = high.isNotEmpty ? weightHigh : 0.0;
      double activeWeightMedium = medium.isNotEmpty ? weightMedium : 0.0;
      double activeWeightLow = low.isNotEmpty ? weightLow : 0.0;
      
      double totalActiveWeight = activeWeightHigh + activeWeightMedium + activeWeightLow;

      if (totalActiveWeight > 0) {
        double shareHigh = activeWeightHigh / totalActiveWeight;
        double shareMedium = activeWeightMedium / totalActiveWeight;
        double shareLow = activeWeightLow / totalActiveWeight;

        double allocateHigh = shareHigh * remainingSurplus;
        double allocateMedium = shareMedium * remainingSurplus;
        double allocateLow = shareLow * remainingSurplus;

        void distributeToGroup(List<Goal> group, double amount) {
          if (group.isEmpty || amount <= 0) return;
          double perGoal = amount / group.length;
          double roundedPerGoal = (perGoal / 10).round() * 10.0; 
          
          for (var g in group) {
            if (totalAllocated + roundedPerGoal > monthlySurplus) {
               roundedPerGoal = monthlySurplus - totalAllocated;
            }
            if (roundedPerGoal < 0) roundedPerGoal = 0;
            
            allocation[g.id!] = roundedPerGoal;
            totalAllocated += roundedPerGoal;
          }
        }

        distributeToGroup(high, allocateHigh);
        distributeToGroup(medium, allocateMedium);
        distributeToGroup(low, allocateLow);
      } else if (emergencyGoal != null) {
        // No other goals, give everything to emergency
        double extra = remainingSurplus;
        allocation[emergencyGoal.id!] = (allocation[emergencyGoal.id!] ?? 0) + extra;
        totalAllocated += extra;
        remainingSurplus = 0;
      }
    }

    return AllocationResult(
      goalIdToMonthlyContribution: allocation,
      totalAllocated: totalAllocated,
      unallocated: max(0, monthlySurplus - totalAllocated),
    );
  }
}
