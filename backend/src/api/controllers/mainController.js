import budgetService from '../../modules/budgets/service.js';
import goalService from '../../modules/goals/service.js';
import investmentService from '../../modules/investments/service.js';
import alertService from '../../modules/alerts/service.js';

// Budget Controllers
export const createBudget = async (req, res) => {
  try {
    const budget = await budgetService.createBudget(req.user.user_id, req.body);
    res.status(201).json({ success: true, data: budget });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const getBudgets = async (req, res) => {
  try {
    const budgets = await budgetService.getBudgets(req.user.user_id);
    res.json({ success: true, data: budgets });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const calculateSavings = async (req, res) => {
  try {
    const savings = await budgetService.calculateSavings(req.user.user_id);
    res.json({ success: true, data: savings });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
};

// Goal Controllers
export const createGoal = async (req, res) => {
  try {
    const goal = await goalService.createGoal(req.user.user_id, req.body);
    res.status(201).json({ success: true, data: goal });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const getGoals = async (req, res) => {
  try {
    const goals = await goalService.getGoals(req.user.user_id);
    res.json({ success: true, data: goals });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const getGoalInsights = async (req, res) => {
  try {
    const insights = await goalService.getGoalInsights(req.user.user_id);
    res.json({ success: true, data: insights });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
};

// Investment Controllers
export const checkInvestmentReadiness = async (req, res) => {
  try {
    const readiness = await investmentService.checkInvestmentReadiness(req.user.user_id);
    res.json({ success: true, data: readiness });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const getInvestmentRecommendations = async (req, res) => {
  try {
    const recommendations = await investmentService.getRecommendations(req.user.user_id);
    res.json({ success: true, data: recommendations });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const addToWatchlist = async (req, res) => {
  try {
    const watchlist = await investmentService.addToWatchlist(req.user.user_id, req.body.instrument_id);
    res.status(201).json({ success: true, data: watchlist });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
};

// Alert Controllers
export const getAlerts = async (req, res) => {
  try {
    const alerts = await alertService.getAlerts(req.user.user_id, req.query.status);
    res.json({ success: true, data: alerts });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const resolveAlert = async (req, res) => {
  try {
    const alert = await alertService.resolveAlert(req.params.alert_id);
    res.json({ success: true, data: alert });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
};
