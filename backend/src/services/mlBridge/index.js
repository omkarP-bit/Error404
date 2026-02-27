import axios from 'axios';
import config from '../../config/env.js';

class MLBridgeService {
  constructor() {
    this.baseURL = config.mlServiceUrl;
  }

  async categorizeTransaction(transactionData) {
    try {
      const response = await axios.post(`${this.baseURL}/categorize`, {
        description: transactionData.raw_description,
        amount: transactionData.amount,
        merchant: transactionData.merchant_name
      });
      return response.data;
    } catch (error) {
      console.error('ML categorization failed:', error.message);
      return { category: 'Uncategorized', confidence: 0, method: 'fallback' };
    }
  }

  async detectAnomaly(userId, transactionData) {
    try {
      const response = await axios.post(`${this.baseURL}/detect-anomaly`, {
        user_id: userId,
        transaction: transactionData
      });
      return response.data;
    } catch (error) {
      console.error('Anomaly detection failed:', error.message);
      return { is_anomalous: false, score: 0 };
    }
  }

  async forecastSpending(userId, category, months = 3) {
    try {
      const response = await axios.post(`${this.baseURL}/forecast`, {
        user_id: userId,
        category,
        months
      });
      return response.data;
    } catch (error) {
      console.error('Forecasting failed:', error.message);
      return { forecast: [], confidence: 0 };
    }
  }

  async calculateGoalFeasibility(userId, goalData) {
    try {
      const response = await axios.post(`${this.baseURL}/goal-feasibility`, {
        user_id: userId,
        goal: goalData
      });
      return response.data;
    } catch (error) {
      console.error('Goal feasibility calculation failed:', error.message);
      return { feasibility_score: 0.5, recommendations: [] };
    }
  }

  async getInvestmentRecommendations(userId) {
    try {
      const response = await axios.post(`${this.baseURL}/investment-recommendations`, {
        user_id: userId
      });
      return response.data;
    } catch (error) {
      console.error('Investment recommendations failed:', error.message);
      return { ready: false, recommendations: [] };
    }
  }
}

export default new MLBridgeService();
