import 'goal_vm.dart';

class SavingsOpportunityVM {
  final String label;
  final double monthlySpend;
  final double suggestedCut;
  final double unlockMonthly;

  SavingsOpportunityVM({
    required this.label,
    required this.monthlySpend,
    required this.suggestedCut,
    required this.unlockMonthly,
  });
}

class InvestmentOverviewVM {
  final bool investmentAllowed;
  final List<String> gateReasons;
  final double monthlyIncome;
  final double avgMonthlyExpense;
  final double avgMonthlySurplus;
  final double safeSipBudget;
  final String riskProfile;
  final int? topGoalHorizonMonths;
  final Map<String, int> allocation;
  final Map<String, double> allocationAmounts;
  final String expectedReturnText;
  final String probabilityText;
  final List<SavingsOpportunityVM> hiddenWealthTop3;
  final double hiddenWealthUnlockMonthly;
  final int monthsSavedForTopGoal;
  final List<GoalVM> goals;

  InvestmentOverviewVM({
    required this.investmentAllowed,
    required this.gateReasons,
    required this.monthlyIncome,
    required this.avgMonthlyExpense,
    required this.avgMonthlySurplus,
    required this.safeSipBudget,
    required this.riskProfile,
    this.topGoalHorizonMonths,
    required this.allocation,
    required this.allocationAmounts,
    required this.expectedReturnText,
    required this.probabilityText,
    required this.hiddenWealthTop3,
    required this.hiddenWealthUnlockMonthly,
    required this.monthsSavedForTopGoal,
    required this.goals,
  });
}
