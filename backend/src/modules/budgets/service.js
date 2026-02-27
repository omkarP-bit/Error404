import db from '../../services/supabase/index.js';
import mlBridge from '../../services/mlBridge/index.js';

class BudgetService {
  async createBudget(userId, budgetData) {
    return await db.insert('budgets', {
      user_id: userId,
      category: budgetData.category,
      limit_amount: budgetData.limit_amount,
      period: budgetData.period || 'monthly',
      is_active: true
    });
  }

  async getBudgets(userId) {
    return await db.query('budgets', {
      eq: { user_id: userId, is_active: true }
    });
  }

  async getBudgetProfile(userId) {
    const profiles = await db.query('budget_profiles', {
      eq: { user_id: userId }
    });
    return profiles[0] || null;
  }

  async calculateSavings(userId) {
    const profile = await this.getBudgetProfile(userId);
    if (!profile) {
      return { safe_amount: 0, message: 'Profile not found' };
    }

    const transactions = await db.query('transactions', {
      eq: { user_id: userId },
      order: { column: 'txn_timestamp', ascending: false },
      limit: 100
    });

    const income = transactions
      .filter(t => t.txn_type === 'credit')
      .reduce((sum, t) => sum + parseFloat(t.amount), 0);

    const expenses = transactions
      .filter(t => t.txn_type === 'debit')
      .reduce((sum, t) => sum + parseFloat(t.amount), 0);

    const surplus = income - expenses;
    const safeAmount = surplus * 0.7;

    await db.update('budget_profiles', profile.profile_id, {
      avg_monthly_surplus: surplus,
      safe_investable_amount: safeAmount
    }, 'profile_id');

    return {
      surplus,
      safe_amount: safeAmount,
      confidence: 0.85,
      explanation: `Based on your spending patterns, you can safely save ₹${safeAmount.toFixed(2)}`
    };
  }

  async autoAllocateBudget(userId, monthlyIncome) {
    const profile = await this.getBudgetProfile(userId);
    const ratios = profile || { needs_ratio: 0.50, wants_ratio: 0.30, savings_ratio: 0.20 };

    const allocation = {
      needs: monthlyIncome * parseFloat(ratios.needs_ratio),
      wants: monthlyIncome * parseFloat(ratios.wants_ratio),
      savings: monthlyIncome * parseFloat(ratios.savings_ratio)
    };

    return allocation;
  }
}

export default new BudgetService();
