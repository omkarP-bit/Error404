import db from '../../services/supabase/index.js';
import mlBridge from '../../services/mlBridge/index.js';

class TransactionService {
  async createTransaction(userId, transactionData) {
    const mlResult = await mlBridge.categorizeTransaction(transactionData);
    
    const transaction = await db.insert('transactions', {
      user_id: userId,
      account_id: transactionData.account_id,
      merchant_id: transactionData.merchant_id,
      amount: transactionData.amount,
      txn_type: transactionData.txn_type,
      category: mlResult.category,
      subcategory: mlResult.subcategory,
      raw_description: transactionData.raw_description,
      clean_description: transactionData.clean_description,
      payment_mode: transactionData.payment_mode,
      confidence_score: mlResult.confidence,
      txn_timestamp: transactionData.txn_timestamp,
      cat_method: mlResult.method,
      ml_metadata: mlResult.metadata
    });

    const anomalyResult = await mlBridge.detectAnomaly(userId, transaction);
    
    if (anomalyResult.is_anomalous) {
      await db.update('transactions', transaction.txn_id, {
        is_anomalous: true,
        anomaly_score: anomalyResult.score
      }, 'txn_id');

      await this.createAlert(userId, transaction.txn_id, anomalyResult);
    }

    await this.updateBudget(userId, transaction.category, transaction.amount);

    return transaction;
  }

  async getTransactions(userId, filters = {}) {
    const options = {
      eq: { user_id: userId },
      order: { column: 'txn_timestamp', ascending: false },
      limit: filters.limit || 50
    };

    if (filters.category) {
      options.eq.category = filters.category;
    }

    return await db.query('transactions', options);
  }

  async updateCategory(txnId, userId, category, subcategory) {
    const transaction = await db.update('transactions', txnId, {
      category,
      subcategory,
      user_verified_category: true
    }, 'txn_id');

    await db.insert('user_feedback', {
      txn_id: txnId,
      corrected_category: category,
      corrected_subcategory: subcategory,
      source: 'user_correction'
    });

    return transaction;
  }

  async createAlert(userId, txnId, anomalyData) {
    return await db.insert('alerts', {
      user_id: userId,
      txn_id: txnId,
      alert_type: 'anomaly',
      severity: anomalyData.score > 0.9 ? 'high' : 'medium',
      status: 'active',
      message: anomalyData.reason || 'Unusual transaction detected'
    });
  }

  async updateBudget(userId, category, amount) {
    const budgets = await db.query('budgets', {
      eq: { user_id: userId, category, is_active: true }
    });

    if (budgets.length > 0) {
      const budget = budgets[0];
      const newSpent = parseFloat(budget.spent_amount) + parseFloat(amount);
      
      await db.update('budgets', budget.budget_id, {
        spent_amount: newSpent
      }, 'budget_id');

      if (newSpent > parseFloat(budget.limit_amount) * 0.8) {
        await db.insert('alerts', {
          user_id: userId,
          alert_type: 'budget_warning',
          severity: newSpent > budget.limit_amount ? 'high' : 'medium',
          status: 'active',
          message: `Budget alert: ${category} spending at ${((newSpent/budget.limit_amount)*100).toFixed(0)}%`
        });
      }
    }
  }
}

export default new TransactionService();
