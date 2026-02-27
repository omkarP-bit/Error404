import db from '../../services/supabase/index.js';
import notificationService from '../../services/notifications/index.js';

class AlertService {
  async getAlerts(userId, status = 'active') {
    return await db.query('alerts', {
      eq: { user_id: userId, status },
      order: { column: 'created_at', ascending: false },
      limit: 50
    });
  }

  async createAlert(userId, alertData) {
    const alert = await db.insert('alerts', {
      user_id: userId,
      txn_id: alertData.txn_id,
      alert_type: alertData.alert_type,
      severity: alertData.severity,
      status: 'active',
      message: alertData.message
    });

    // Send notifications via Supabase SMTP
    await notificationService.sendAlert(
      userId,
      alertData.alert_type,
      alertData.severity,
      alertData.message
    );

    // Log notification
    await db.insert('notification_log', {
      alert_id: alert.alert_id,
      user_id: userId,
      channel: alertData.severity === 'high' ? 'email' : 'push',
      sent_at: new Date().toISOString()
    });

    return alert;
  }

  async resolveAlert(alertId) {
    return await db.update('alerts', alertId, {
      status: 'resolved',
      resolved_at: new Date().toISOString()
    }, 'alert_id');
  }
}

export default new AlertService();
