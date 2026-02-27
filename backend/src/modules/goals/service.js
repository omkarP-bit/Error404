import db from '../../services/supabase/index.js';
import mlBridge from '../../services/mlBridge/index.js';

class GoalService {
  async createGoal(userId, goalData) {
    const feasibility = await mlBridge.calculateGoalFeasibility(userId, goalData);
    
    return await db.insert('goals', {
      user_id: userId,
      goal_name: goalData.goal_name,
      target_amount: goalData.target_amount,
      current_amount: goalData.current_amount || 0,
      deadline: goalData.deadline,
      status: 'active',
      feasibility_score: feasibility.feasibility_score
    });
  }

  async getGoals(userId) {
    return await db.query('goals', {
      eq: { user_id: userId, status: 'active' },
      order: { column: 'deadline', ascending: true }
    });
  }

  async updateGoalProgress(goalId, amount) {
    const goals = await db.query('goals', { eq: { goal_id: goalId } });
    const goal = goals[0];
    
    const newAmount = parseFloat(goal.current_amount) + parseFloat(amount);
    const updated = await db.update('goals', goalId, {
      current_amount: newAmount,
      status: newAmount >= parseFloat(goal.target_amount) ? 'completed' : 'active'
    }, 'goal_id');

    return updated;
  }

  async getGoalInsights(userId) {
    const goals = await this.getGoals(userId);
    const profile = await db.query('budget_profiles', { eq: { user_id: userId } });
    
    if (!profile[0]) {
      return { ready: false, message: 'Complete your profile first' };
    }

    const insights = goals.map(goal => {
      const remaining = parseFloat(goal.target_amount) - parseFloat(goal.current_amount);
      const daysLeft = Math.ceil((new Date(goal.deadline) - new Date()) / (1000 * 60 * 60 * 24));
      const monthlyRequired = remaining / (daysLeft / 30);
      
      return {
        goal_id: goal.goal_id,
        goal_name: goal.goal_name,
        progress: (parseFloat(goal.current_amount) / parseFloat(goal.target_amount) * 100).toFixed(1),
        monthly_required: monthlyRequired,
        feasibility: goal.feasibility_score,
        on_track: monthlyRequired <= parseFloat(profile[0].safe_investable_amount)
      };
    });

    return insights;
  }
}

export default new GoalService();
