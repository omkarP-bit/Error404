import db from '../../services/supabase/index.js';
import mlBridge from '../../services/mlBridge/index.js';

class InvestmentService {
  async checkInvestmentReadiness(userId) {
    const profile = await db.query('budget_profiles', { eq: { user_id: userId } });
    const goals = await db.query('goals', { eq: { user_id: userId, status: 'active' } });
    const alerts = await db.query('alerts', { 
      eq: { user_id: userId, status: 'active', severity: 'high' } 
    });

    if (!profile[0]) {
      return { ready: false, reason: 'Profile incomplete', gates: {} };
    }

    const p = profile[0];
    const emergencyFund = parseFloat(p.baseline_expense) * 6;
    const hasEmergencyFund = parseFloat(p.avg_monthly_surplus) >= emergencyFund / 12;
    const hasPositiveSurplus = parseFloat(p.avg_monthly_surplus) > 0;
    const lowVolatility = parseFloat(p.expense_volatility) < parseFloat(p.baseline_expense) * 0.3;
    const noHighRiskAlerts = alerts.length === 0;

    const gates = {
      emergency_fund: hasEmergencyFund,
      positive_surplus: hasPositiveSurplus,
      low_volatility: lowVolatility,
      no_high_risk: noHighRiskAlerts
    };

    const allPassed = Object.values(gates).every(v => v);

    return {
      ready: allPassed,
      gates,
      investable_amount: allPassed ? parseFloat(p.safe_investable_amount) : 0,
      reason: allPassed ? 'All checks passed' : 'Some requirements not met'
    };
  }

  async getRecommendations(userId) {
    const readiness = await this.checkInvestmentReadiness(userId);
    
    if (!readiness.ready) {
      return { ready: false, recommendations: [], reason: readiness.reason };
    }

    const mlRecommendations = await mlBridge.getInvestmentRecommendations(userId);
    
    const instruments = await db.query('mf_instruments', {
      limit: 10,
      order: { column: 'cagr_3y', ascending: false }
    });

    const recommendations = instruments.map(inst => ({
      instrument_id: inst.instrument_id,
      name: inst.name,
      risk_level: inst.risk_level,
      expected_return: inst.cagr_3y,
      sip_minimum: inst.sip_minimum,
      recommended_amount: Math.min(readiness.investable_amount * 0.3, 10000)
    }));

    return {
      ready: true,
      investable_amount: readiness.investable_amount,
      recommendations
    };
  }

  async addToWatchlist(userId, instrumentId) {
    return await db.insert('mf_watchlist', {
      user_id: userId,
      instrument_id: instrumentId
    });
  }

  async getWatchlist(userId) {
    const watchlist = await db.query('mf_watchlist', { eq: { user_id: userId } });
    
    const instruments = await Promise.all(
      watchlist.map(async (w) => {
        const inst = await db.query('mf_instruments', { eq: { instrument_id: w.instrument_id } });
        return inst[0];
      })
    );

    return instruments;
  }
}

export default new InvestmentService();
