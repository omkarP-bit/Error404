import 'dart:math';
import 'local_momentum_db.dart';

class MomentumResult {
  final int streakMonths;        // consecutive contributed months ending in current month
  final double consistencyPct;   // contributed months / last N months
  final int missedMonths;        // count of months marked missed in last N months
  final int score;               // 0..100

  MomentumResult({
    required this.streakMonths,
    required this.consistencyPct,
    required this.missedMonths,
    required this.score,
  });
}

class MomentumEngine {
  MomentumResult compute({
    required List<SavingsActivity> lastMonths,
    required String currentMonthKey,
    int windowMonths = 6,
  }) {
    // We expect lastMonths to be pre-filled with 0-contribution defaults if missing,
    // and ordered descending (newest first).

    // 1. Calculate streak (consecutive months contributed starting from now backwards)
    int streak = 0;
    for (var activity in lastMonths) {
      if (activity.contributed) {
        streak++;
      } else {
        break; // Streak broken
      }
    }

    // 2. Calculate consistency (percentage of contributed months in the window)
    int contributedCount = lastMonths.where((a) => a.contributed).length;
    double consistencyPct = windowMonths > 0 ? (contributedCount / windowMonths) * 100 : 0.0;

    // 3. Count missed months
    int missedCount = lastMonths.where((a) => a.missed).length;

    // 4. Calculate score
    // - streakScore = min(40, streakMonths * 10)  
    double streakScore = min(40.0, streak * 10.0);
    // - consistencyScore = round(consistencyPct * 0.5)
    double consistencyScore = (consistencyPct * 0.5).roundToDouble();
    // - penalty = missedMonths * 10
    double penalty = missedCount * 10.0;
    
    // - score = clamp( streakScore + consistencyScore - penalty, 0, 100 )
    int score = (streakScore + consistencyScore - penalty).clamp(0.0, 100.0).toInt();

    return MomentumResult(
      streakMonths: streak,
      consistencyPct: consistencyPct,
      missedMonths: missedCount,
      score: score,
    );
  }
}
