#!/usr/bin/env python3
"""
Train all ML models for the Personal Finance Platform
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from models.categorization.categorizer import CategorizationModel
from models.anomaly_detection.detector import AnomalyDetectionModel
from models.goal_planning.feasibility import GoalProbabilityModel

def generate_sample_data():
    """Generate sample training data for models."""
    
    # Sample categories
    categories = [
        'Food & Dining', 'Shopping', 'Transportation', 'Bills & Utilities',
        'Entertainment', 'Healthcare', 'Education', 'Investment', 'Transfer', 'Salary'
    ]
    
    # Sample merchants
    merchants = {
        'Food & Dining': ['Swiggy', 'Zomato', 'McDonald', 'Starbucks'],
        'Shopping': ['Amazon', 'Flipkart', 'DMart', 'Reliance'],
        'Transportation': ['Uber', 'Ola', 'Petrol Pump', 'Metro'],
        'Bills & Utilities': ['Electricity', 'Water', 'Internet', 'Mobile'],
        'Entertainment': ['Netflix', 'Spotify', 'BookMyShow', 'Prime'],
    }
    
    # Generate transaction data
    n_samples = 1000
    data = []
    
    for _ in range(n_samples):
        category = np.random.choice(categories)
        merchant_list = merchants.get(category, ['Generic'])
        merchant = np.random.choice(merchant_list)
        
        amount = np.random.uniform(50, 5000)
        month = np.random.randint(1, 13)
        day_of_week = np.random.randint(0, 7)
        hour = np.random.randint(0, 24)
        
        text_input = f"{merchant} payment transaction"
        
        data.append({
            'text_input': text_input,
            'amount': amount,
            'month': month,
            'day_of_week': day_of_week,
            'hour': hour,
            'category': category,
        })
    
    return pd.DataFrame(data)

def train_categorization_model():
    """Train the categorization model."""
    print("\n" + "="*60)
    print("Training Categorization Model")
    print("="*60)
    
    df = generate_sample_data()
    X = df.drop('category', axis=1)
    y = df['category']
    
    model = CategorizationModel()
    model.train(X, y)
    
    print("✅ Categorization model trained successfully")

def train_anomaly_model():
    """Train the anomaly detection model."""
    print("\n" + "="*60)
    print("Training Anomaly Detection Model")
    print("="*60)
    
    # Generate anomaly features
    n_samples = 1000
    features = pd.DataFrame({
        'amount_deviation': np.random.randn(n_samples),
        'time_anomaly': np.random.randint(0, 2, n_samples),
        'frequency_spike': np.random.uniform(0, 1, n_samples),
        'category_variance': np.random.randn(n_samples),
        'rolling_deviation': np.random.randn(n_samples),
    })
    
    model = AnomalyDetectionModel()
    report = model.train(features)
    
    print(f"   Anomalies found: {report['anomalies_found']} ({report['anomaly_rate']:.1%})")
    print("✅ Anomaly detection model trained successfully")

def train_goal_model():
    """Train the goal feasibility model."""
    print("\n" + "="*60)
    print("Training Goal Feasibility Model")
    print("="*60)
    
    # Generate goal features
    n_samples = 500
    features = pd.DataFrame({
        'feasibility_ratio': np.random.uniform(0.5, 2.0, n_samples),
        'months_left': np.random.uniform(1, 36, n_samples),
        'avg_monthly_surplus': np.random.uniform(5000, 50000, n_samples),
        'expense_volatility_ratio': np.random.uniform(0.1, 0.5, n_samples),
        'current_progress': np.random.uniform(0, 0.8, n_samples),
    })
    
    # Generate labels (achieved or not)
    y = (features['feasibility_ratio'] > 1.0).astype(int)
    
    model = GoalProbabilityModel()
    report = model.train(features, y)
    
    print(f"   AUC: {report['auc']:.4f}")
    print("✅ Goal feasibility model trained successfully")

if __name__ == "__main__":
    print("\n🚀 Starting ML Model Training Pipeline")
    print("="*60)
    
    try:
        train_categorization_model()
        train_anomaly_model()
        train_goal_model()
        
        print("\n" + "="*60)
        print("✅ All models trained successfully!")
        print("="*60)
        print("\nModels saved to:")
        print("  • ml/src/models/categorization/artifacts/")
        print("  • ml/src/models/anomaly_detection/artifacts/")
        print("  • ml/src/models/goal_planning/artifacts/")
        print("\nYou can now start the ML service with:")
        print("  python ml/src/api/main.py")
        
    except Exception as e:
        print(f"\n❌ Error during training: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
