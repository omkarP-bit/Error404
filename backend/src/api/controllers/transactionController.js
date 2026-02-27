import transactionService from '../../modules/transactions/service.js';

export const createTransaction = async (req, res) => {
  try {
    const transaction = await transactionService.createTransaction(req.user.user_id, req.body);
    res.status(201).json({ success: true, data: transaction });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const getTransactions = async (req, res) => {
  try {
    const transactions = await transactionService.getTransactions(req.user.user_id, req.query);
    res.json({ success: true, data: transactions });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
};

export const updateTransactionCategory = async (req, res) => {
  try {
    const { txn_id } = req.params;
    const { category, subcategory } = req.body;
    const transaction = await transactionService.updateCategory(txn_id, req.user.user_id, category, subcategory);
    res.json({ success: true, data: transaction });
  } catch (error) {
    res.status(500).json({ success: false, error: error.message });
  }
};
