import express from 'express';
import { authenticate, authorize } from '../middlewares/auth.js';
import * as adminController from '../controllers/adminController.js';
import * as analyticsController from '../controllers/analyticsController.js';

const router = express.Router();

// All routes require admin role
router.use(authenticate);
router.use(authorize('admin'));

router.get('/dashboard/embed-url', adminController.getDashboardUrl);
router.get('/metrics/system', adminController.getSystemMetrics);
router.post('/analytics/export', analyticsController.exportToS3);

export default router;
