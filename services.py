import base64
import re
from collections import defaultdict
from datetime import datetime
from email.utils import parsedate_to_datetime

def normalize_merchant(name):
    """
    Clean merchant names to avoid duplicates.
    """
    name = name.lower()

    # Remove email part if present
    if "<" in name:
        name = name.split("<")[0]

    # Remove common noise
    name = name.replace('"', '')
    name = name.replace('*', '')
    name = name.replace(" india", "")
    name = name.replace(" private limited", "")
    name = name.strip()

    return name


def extract_transactions(service):

    results = service.users().messages().list(
        userId="me",
        maxResults=50
    ).execute()

    messages = results.get("messages", [])
    transactions = []

    def extract_body(payload):
        if "parts" in payload:
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain" and "data" in part["body"]:
                    data = part["body"]["data"]
                    return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        elif "body" in payload and "data" in payload["body"]:
            data = payload["body"]["data"]
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
        return ""

    for msg in messages:
        message = service.users().messages().get(
            userId="me",
            id=msg["id"],
            format="full"
        ).execute()

        headers = message.get("payload", {}).get("headers", [])
        sender = ""
        date_value = ""

        for header in headers:
            if header["name"] == "From":
                raw_sender = header["value"]
                sender = raw_sender.split("<")[0].replace('"', '').strip()

            if header["name"] == "Date":
                date_value = header["value"]

        body_text = extract_body(message["payload"])
        amount_match = re.search(r'₹\s?\d+[\.,]?\d*', body_text)

        if amount_match:
            amount_str = amount_match.group()
            numeric_amount = int(amount_str.replace("₹", "").replace(",", "").strip())

            try:
                parsed_date = parsedate_to_datetime(date_value)
                date_iso = parsed_date.date().isoformat()
            except:
                date_iso = None

            normalized = normalize_merchant(sender)

            transactions.append({
                "merchant": normalized,
                "amount": numeric_amount,
                "date": date_iso
            })

    return transactions


def build_subscriptions(transactions):

    from collections import defaultdict
    from datetime import datetime

    merchant_groups = defaultdict(list)

    # Group by merchant + amount
    for tx in transactions:
        if tx["date"]:
            merchant_groups[(tx["merchant"], tx["amount"])].append(tx)

    subscriptions = []

    for (merchant, amount), tx_list in merchant_groups.items():

        if len(tx_list) < 2:
            continue

        # Sort by date
        tx_list.sort(key=lambda x: x["date"])

        dates = [
            datetime.fromisoformat(tx["date"])
            for tx in tx_list
            if tx["date"]
        ]

        if len(dates) < 2:
            continue

        # Calculate intervals between consecutive payments
        gaps = []
        for i in range(1, len(dates)):
            gaps.append((dates[i] - dates[i - 1]).days)

        avg_gap = sum(gaps) / len(gaps)

        # Determine billing cycle
        billing_cycle = "unknown"

        if 25 <= avg_gap <= 35:
            billing_cycle = "monthly"
        elif 330 <= avg_gap <= 380:
            billing_cycle = "yearly"

        # ---- Confidence Score Logic ----
        # More transactions = more confidence
        freq_score = min(len(tx_list) * 20, 60)

        # Gap stability bonus
        stability_score = 0

        if len(gaps) >= 1:
            variance = max(gaps) - min(gaps)
            if variance <= 5:
                stability_score = 30
            elif variance <= 15:
                stability_score = 15

        # Cycle clarity bonus
        cycle_score = 10 if billing_cycle != "unknown" else 0

        confidence = min(freq_score + stability_score + cycle_score, 100)

        # ---- Active / Inactive logic ----
        last_payment = dates[-1]
        days_since_last = (datetime.now() - last_payment).days

        if billing_cycle == "monthly" and days_since_last > 60:
            status = "likely_cancelled"
        elif billing_cycle == "yearly" and days_since_last > 400:
            status = "likely_cancelled"
        else:
            status = "active"

        # ---- Cost Calculation ----
        if billing_cycle == "monthly":
            monthly_cost = amount
            yearly_cost = amount * 12
        elif billing_cycle == "yearly":
            monthly_cost = round(amount / 12, 2)
            yearly_cost = amount
        else:
            monthly_cost = amount
            yearly_cost = amount * 12

        subscriptions.append({
            "merchant": merchant,
            "monthly_cost": monthly_cost,
            "yearly_cost": yearly_cost,
            "billing_cycle": billing_cycle,
            "transaction_count": len(tx_list),
            "avg_interval_days": round(avg_gap, 2),
            "confidence_score": confidence,
            "last_payment_date": last_payment.date().isoformat(),
            "status": status
        })

    # Sort by highest yearly cost (important subscriptions first)
    subscriptions.sort(key=lambda x: x["yearly_cost"], reverse=True)

    return subscriptions


def calculate_summary(subscriptions):

    if not subscriptions:
        return {
            "total_monthly": 0,
            "total_yearly": 0,
            "active_count": 0,
            "most_expensive_subscription": None,
            "highest_confidence_subscription": None,
            "likely_cancelled_count": 0
        }

    total_monthly = sum(sub["monthly_cost"] for sub in subscriptions)
    total_yearly = sum(sub["yearly_cost"] for sub in subscriptions)

    active_count = len([s for s in subscriptions if s["status"] == "active"])
    cancelled_count = len([s for s in subscriptions if s["status"] == "likely_cancelled"])

    most_expensive = max(subscriptions, key=lambda x: x["yearly_cost"])
    highest_confidence = max(subscriptions, key=lambda x: x.get("confidence_score", 0))

    return {
        "total_monthly": total_monthly,
        "total_yearly": total_yearly,
        "active_count": active_count,
        "likely_cancelled_count": cancelled_count,
        "most_expensive_subscription": most_expensive["merchant"],
        "highest_confidence_subscription": highest_confidence["merchant"]
    }