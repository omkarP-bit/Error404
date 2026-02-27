from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.categorization.categorizer import CategorizationModel
from models.anomaly_detection.detector import AnomalyDetectionModel
from models.forecasting.forecaster import SpendingForecaster
from models.goal_planning.feasibility import GoalProbabilityModel

app = FastAPI(title="Personal Finance ML Service", version="2.0.0")

# Initialize models
categorizer = CategorizationModel()
anomaly_detector = AnomalyDetectionModel()
forecaster = SpendingForecaster()
goal_calculator = GoalProbabilityModel()

# Load models if trained
if categorizer.is_trained():
    categorizer.load()
if anomaly_detector.is_trained():
    anomaly_detector.load()
if goal_calculator.is_trained():
    goal_calculator.load()

# Pydantic models
class TransactionInput(BaseModel):
    description: str
    amount: Optional[float] = None
    merchant: Optional[str] = None
    month: Optional[int] = 1
    day_of_week: Optional[int] = 0
    hour: Optional[int] = 12

class AnomalyInput(BaseModel):
    user_id: int
    transaction: Dict
    user_history: Optional[List[Dict]] = []

class ForecastInput(BaseModel):
    user_id: int
    category: Optional[str] = 'all'
    user_history: List[Dict]
    months: Optional[int] = 3

class GoalInput(BaseModel):
    user_id: int
    goal: Dict
    user_profile: Optional[Dict] = None
    user_history: Optional[List[Dict]] = []

@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "Personal Finance ML Service",
        "version": "2.0.0",
        "models": {
            "categorization": "TF-IDF + LinearSVC + SentenceTransformer",
            "anomaly_detection": "IsolationForest",
            "forecasting": "Time-series",
            "goal_feasibility": "HistGradientBoosting + LogisticRegression"
        }
    }

@app.post("/categorize")
def categorize_transaction(data: TransactionInput):
    try:
        result = categorizer.predict_single(
            text_input=data.description,
            amount=data.amount or 0,
            merchant_name=data.merchant or "",
            month=data.month,
            day_of_week=data.day_of_week,
            hour=data.hour,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/detect-anomaly")
def detect_anomaly(data: AnomalyInput):
    try:
        result = anomaly_detector.detect(
            user_id=data.user_id,
            transaction=data.transaction,
            user_history=data.user_history
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/forecast")
def forecast_spending(data: ForecastInput):
    try:
        result = forecaster.forecast(
            user_id=data.user_id,
            category=data.category,
            user_history=data.user_history,
            months=data.months
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/goal-feasibility")
def calculate_goal_feasibility(data: GoalInput):
    try:
        result = goal_calculator.calculate(
            user_id=data.user_id,
            goal=data.goal,
            user_profile=data.user_profile,
            user_history=data.user_history
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/investment-recommendations")
def get_investment_recommendations(data: Dict):
    return {
        "ready": True,
        "recommendations": [],
        "message": "Investment recommendations based on risk profile"
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "models_loaded": {
            "categorization": categorizer._fitted,
            "anomaly_detection": anomaly_detector._fitted,
            "goal_feasibility": goal_calculator._fitted,
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
