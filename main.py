from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from services import extract_transactions, build_subscriptions, calculate_summary
import os


app = FastAPI()
transactions_store = []
subscriptions_store = []

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

CLIENT_SECRET_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
REDIRECT_URI = "http://localhost:8000/auth/callback"

@app.get("/")
def read_root():
    return {"message": "Gmail Subscription Backend Running"}

@app.get("/connect-gmail")
def connect_gmail():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
    )

    return RedirectResponse(auth_url)

@app.get("/auth/callback")
def auth_callback(request: Request):

    global transactions_store, subscriptions_store

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    flow.fetch_token(authorization_response=str(request.url))
    credentials = flow.credentials

    service = build("gmail", "v1", credentials=credentials)

    transactions = extract_transactions(service)
    subscriptions = build_subscriptions(transactions)
    summary = calculate_summary(subscriptions)

    transactions_store = transactions
    subscriptions_store = subscriptions

    return JSONResponse({
        "status": "Gmail connected successfully",
        "transactions_detected": len(transactions),
        "subscriptions": subscriptions,
        "summary": summary
    })


# OUTSIDE CALLBACK (no indentation)
@app.get("/transactions")
def get_transactions():
    return {"transactions": transactions_store}


@app.get("/subscriptions")
def get_subscriptions():
    return {"subscriptions": subscriptions_store}


@app.get("/subscriptions/summary")
def get_summary():
    summary = calculate_summary(subscriptions_store)
    return {"summary": summary}

from pydantic import BaseModel


class ManualSubscription(BaseModel):
    merchant: str
    amount: float
    billing_cycle: str  # monthly / yearly


@app.post("/subscriptions/manual")
def add_manual_subscription(subscription: ManualSubscription):

    global subscriptions_store

    if subscription.billing_cycle == "monthly":
        monthly_cost = subscription.amount
        yearly_cost = subscription.amount * 12
    elif subscription.billing_cycle == "yearly":
        monthly_cost = round(subscription.amount / 12, 2)
        yearly_cost = subscription.amount
    else:
        return {"error": "billing_cycle must be monthly or yearly"}

    new_entry = {
        "merchant": subscription.merchant.lower(),
        "monthly_cost": monthly_cost,
        "yearly_cost": yearly_cost,
        "billing_cycle": subscription.billing_cycle,
        "transaction_count": 1,
        "avg_interval_days": None,
        "confidence_score": 50,
        "last_payment_date": None,
        "status": "manually_added"
    }

    subscriptions_store.append(new_entry)

    return {
        "message": "Manual subscription added successfully",
        "subscription": new_entry
    }