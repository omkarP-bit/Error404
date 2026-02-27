import db from '../../services/supabase/index.js';
import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';
import config from '../../config/env.js';

const s3 = new S3Client({ region: config.aws.region });

export const exportToS3 = async (req, res) => {
  try {
    if (req.user.role !== 'admin') {
      return res.status(403).json({ error: 'Admin access required' });
    }

    const views = [
      'vw_transaction_analytics',
      'vw_user_financial_health',
      'vw_ml_model_performance',
      'vw_category_distribution',
      'vw_anomaly_metrics',
      'vw_budget_performance',
      'vw_goal_metrics',
      'vw_system_metrics'
    ];

    const date = new Date().toISOString().split('T')[0];
    const exported = [];

    for (const view of views) {
      const data = await db.query(view, { limit: 10000 });
      const csv = convertToCSV(data);
      
      await s3.send(new PutObjectCommand({
        Bucket: process.env.S3_ANALYTICS_BUCKET || 'personal-finance-analytics',
        Key: `${view}/${date}.csv`,
        Body: csv,
        ContentType: 'text/csv'
      }));

      exported.push(view);
    }

    res.json({ 
      success: true, 
      message: 'Data exported to S3',
      views: exported,
      date 
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

function convertToCSV(data) {
  if (!data || data.length === 0) return '';
  
  const headers = Object.keys(data[0]).join(',');
  const rows = data.map(row => 
    Object.values(row).map(val => 
      typeof val === 'string' && val.includes(',') ? `"${val}"` : val
    ).join(',')
  );
  
  return [headers, ...rows].join('\n');
}
