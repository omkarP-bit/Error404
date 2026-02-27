import numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

class SpendingForecaster:
    def forecast(self, user_id, category, user_history, months=3):
        if not user_history or len(user_history) < 30:
            return {'forecast': [], 'confidence': 0, 'message': 'Insufficient data'}
        
        # Filter by category if specified
        if category and category != 'all':
            transactions = [t for t in user_history if t.get('category') == category]
        else:
            transactions = user_history
        
        if len(transactions) < 10:
            return {'forecast': [], 'confidence': 0, 'message': 'Insufficient category data'}
        
        # Group by month
        monthly_spending = defaultdict(float)
        for txn in transactions:
            if txn['txn_type'] == 'debit':
                date = datetime.fromisoformat(txn['txn_timestamp'].replace('Z', '+00:00'))
                month_key = date.strftime('%Y-%m')
                monthly_spending[month_key] += float(txn['amount'])
        
        # Calculate trend
        amounts = list(monthly_spending.values())
        if len(amounts) < 3:
            avg_spending = np.mean(amounts)
            trend = 0
        else:
            # Simple linear trend
            x = np.arange(len(amounts))
            y = np.array(amounts)
            trend = np.polyfit(x, y, 1)[0]
            avg_spending = np.mean(amounts[-3:])  # Last 3 months average
        
        # Generate forecast
        forecast = []
        current_date = datetime.now()
        
        for i in range(months):
            future_date = current_date + timedelta(days=30 * (i + 1))
            predicted_amount = avg_spending + (trend * (i + 1))
            predicted_amount = max(predicted_amount, 0)  # No negative predictions
            
            forecast.append({
                'month': future_date.strftime('%Y-%m'),
                'predicted_amount': round(predicted_amount, 2),
                'lower_bound': round(predicted_amount * 0.8, 2),
                'upper_bound': round(predicted_amount * 1.2, 2)
            })
        
        # Calculate confidence based on data consistency
        std_dev = np.std(amounts)
        mean_amount = np.mean(amounts)
        cv = std_dev / mean_amount if mean_amount > 0 else 1
        confidence = max(0, min(1, 1 - cv))
        
        return {
            'forecast': forecast,
            'confidence': round(confidence, 2),
            'trend': 'increasing' if trend > 0 else 'decreasing' if trend < 0 else 'stable',
            'avg_monthly': round(avg_spending, 2)
        }
