import express from 'express';
import { authenticate } from '../middlewares/auth.js';
import * as controller from '../controllers/mainController.js';

const router = express.Router();

// Budget routes
router.post('/budgets', authenticate, controller.createBudget);
router.get('/budgets', authenticate, controller.getBudgets);
router.get('/budgets/savings', authenticate, controller.calculateSavings);

// Goal routes
router.post('/goals', authenticate, controller.createGoal);
router.get('/goals', authenticate, controller.getGoals);
router.get('/goals/insights', authenticate, controller.getGoalInsights);

// Investment routes
router.get('/investments/readiness', authenticate, controller.checkInvestmentReadiness);
router.get('/investments/recommendations', authenticate, controller.getInvestmentRecommendations);
router.post('/investments/watchlist', authenticate, controller.addToWatchlist);

// Alert routes
router.get('/alerts', authenticate, controller.getAlerts);
router.patch('/alerts/:alert_id/resolve', authenticate, controller.resolveAlert);

export default router;
