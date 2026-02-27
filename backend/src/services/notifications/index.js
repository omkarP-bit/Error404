import { supabaseAdmin } from '../../config/supabase.js';

class NotificationService {
  async sendEmail(userId, subject, message) {
    try {
      // Get user email
      const { data: user } = await supabaseAdmin
        .from('users')
        .select('email, name')
        .eq('user_id', userId)
        .single();

      if (!user) {
        throw new Error('User not found');
      }

      // Send email via Supabase Auth (uses configured SMTP)
      const { error } = await supabaseAdmin.auth.admin.sendEmail({
        email: user.email,
        subject: subject,
        html: `
          <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #6C63FF;">Personal Finance Alert</h2>
            <p>Hi ${user.name},</p>
            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
              ${message}
            </div>
            <p style="color: #666; font-size: 12px;">
              This is an automated notification from your Personal Finance Platform.
            </p>
          </div>
        `
      });

      if (error) throw error;

      return { success: true, channel: 'email' };
    } catch (error) {
      console.error('Email notification failed:', error.message);
      return { success: false, error: error.message };
    }
  }

  async sendPushNotification(userId, title, body) {
    // Push notification implementation (FCM, OneSignal, etc.)
    // For now, just log
    console.log(`Push notification to user ${userId}: ${title}`);
    return { success: true, channel: 'push' };
  }

  async sendAlert(userId, alertType, severity, message) {
    const notifications = [];

    // High severity: send email
    if (severity === 'high' || severity === 'critical') {
      const emailResult = await this.sendEmail(
        userId,
        `${severity.toUpperCase()} Alert: ${alertType}`,
        message
      );
      notifications.push(emailResult);
    }

    // Always send push notification
    const pushResult = await this.sendPushNotification(
      userId,
      `${alertType} Alert`,
      message
    );
    notifications.push(pushResult);

    return notifications;
  }
}

export default new NotificationService();
