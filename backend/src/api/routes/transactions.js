import express from 'express';
import { authenticate } from '../middlewares/auth.js';
import * as transactionController from '../controllers/transactionController.js';

const router = express.Router();

router.post('/', authenticate, transactionController.createTransaction);
router.get('/', authenticate, transactionController.getTransactions);
router.patch('/:txn_id/category', authenticate, transactionController.updateTransactionCategory);

export default router;
