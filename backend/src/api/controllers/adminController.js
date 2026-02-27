import quicksightService from '../../services/quicksight/index.js';
import db from '../../services/supabase/index.js';

export const getDashboardUrl = async (req, res) => {
  try {
    // Only admins can access
    if (req.user.role !== 'admin') {
      return res.status(403).json({ error: 'Admin access required' });
    }

    const embedUrl = await quicksightService.getEmbedUrl(req.user.email);
    
    // Log access
    await db.insert('audit_logs', {
      actor_id: req.user.user_id,
      actor_type: 'admin',
      action: 'dashboard_access',
      resource_type: 'quicksight_dashboard',
      ip_address: req.ip,
    });

    res.json({ 
      success: true, 
      data: embedUrl 
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};

export const getSystemMetrics = async (req, res) => {
  try {
    if (req.user.role !== 'admin') {
      return res.status(403).json({ error: 'Admin access required' });
    }

    // Get aggregated metrics from anonymized views
    const metrics = await db.query('vw_system_metrics', {
      limit: 100,
      order: { column: 'metric_hour', ascending: false }
    });

    res.json({ success: true, data: metrics });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
};
