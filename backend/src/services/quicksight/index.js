import { QuickSightClient, GenerateEmbedUrlForRegisteredUserCommand } from '@aws-sdk/client-quicksight';
import config from '../../config/env.js';

class QuickSightService {
  constructor() {
    this.client = new QuickSightClient({
      region: config.aws.region,
      credentials: {
        accessKeyId: process.env.AWS_ACCESS_KEY_ID,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
      }
    });
    
    this.awsAccountId = process.env.AWS_ACCOUNT_ID;
    this.dashboardId = process.env.AWS_QUICKSIGHT_DASHBOARD_ID;
    this.namespace = process.env.AWS_QUICKSIGHT_NAMESPACE || 'default';
  }

  async getEmbedUrl(userEmail, sessionLifetime = 15) {
    try {
      const command = new GenerateEmbedUrlForRegisteredUserCommand({
        AwsAccountId: this.awsAccountId,
        UserArn: `arn:aws:quicksight:${config.aws.region}:${this.awsAccountId}:user/${this.namespace}/${userEmail}`,
        SessionLifetimeInMinutes: sessionLifetime,
        ExperienceConfiguration: {
          Dashboard: {
            InitialDashboardId: this.dashboardId,
          }
        }
      });

      const response = await this.client.send(command);
      
      return {
        embedUrl: response.EmbedUrl,
        expiresAt: new Date(Date.now() + sessionLifetime * 60 * 1000),
      };
    } catch (error) {
      console.error('QuickSight embed URL generation failed:', error);
      throw new Error('Failed to generate dashboard URL');
    }
  }
}

export default new QuickSightService();
