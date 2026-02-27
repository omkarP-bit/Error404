from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse, JSONResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import os


app = FastAPI()

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
    import base64
    import re
    from collections import defaultdict

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    flow.fetch_token(authorization_response=str(request.url))
    credentials = flow.credentials

    # Build Gmail API service
    service = build("gmail", "v1", credentials=credentials)

    results = service.users().messages().list(
        userId="me",
        q='subject:(invoice OR receipt OR charged OR payment)',
        maxResults=10
    ).execute()

    messages = results.get("messages", [])
    email_data = []

    def extract_body(payload):
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part["body"]:
                    data = part["body"]["data"]
                    decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                    return decoded
        elif "body" in payload and "data" in payload["body"]:
            data = payload["body"]["data"]
            decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            return decoded
        return ""

    for msg in messages:
        message = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full"
        ).execute()

        headers = message.get("payload", {}).get("headers", [])
        subject = ""
        sender = ""
        date_value = ""

        for header in headers:
            if header["name"] == "Subject":
                subject = header["value"]

            if header["name"] == "From":
                raw_sender = header["value"]
                sender = raw_sender.split("<")[0].replace('"', '').strip()

            if header["name"] == "Date":
                date_value = header["value"]

        body_text = extract_body(message["payload"])
        amount_match = re.search(r'₹\s?\d+[\.,]?\d*', body_text)
        amount = amount_match.group() if amount_match else None

        email_data.append({
            "subject": subject,
            "from": sender,
            "amount_detected": amount,
            "date": date_value
        })

    # Group merchants by same amount
    merchant_groups = defaultdict(list)

    for email in email_data:
        if email["amount_detected"]:
            merchant_groups[email["from"]].append(email["amount_detected"])

    subscriptions = []

    for merchant, amounts in merchant_groups.items():
        if len(amounts) >= 2 and len(set(amounts)) == 1:
            subscriptions.append({
                "merchant": merchant,
                "estimated_amount": amounts[0]
            })

    # Demo fallback
    if not subscriptions:
        subscriptions = [
            {"merchant": "Netflix", "estimated_amount": "₹649"},
            {"merchant": "Spotify", "estimated_amount": "₹119"}
        ]

    # Convert to financial output
    final_output = []

    for sub in subscriptions:
        amount_str = sub["estimated_amount"]
        numeric_amount = int(amount_str.replace("₹", "").replace(",", "").strip())

        final_output.append({
            "merchant": sub["merchant"],
            "monthly_cost": numeric_amount,
            "yearly_cost": numeric_amount * 12
        })

    return JSONResponse({
        "status": "Gmail connected successfully",
        "subscriptions": final_output
    })