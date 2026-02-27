"""
app/services/categorization_service.py
=======================================
4-Stage Hybrid Categorization Pipeline
──────────────────────────────────────
Stage 1 │ DB Merchant Lookup + User CategoryMapping  (always first, highest confidence)
Stage 2 │ Sentence Transformers — primary NLP model  (semantic similarity)
Stage 3 │ TF-IDF + LinearSVC                         (fast trained fallback)
Stage 4 │ Confidence-aware human-in-the-loop         (< 0.85 → ask user)

Feedback Loop (immediate, not batch):
  confirm_category() → upserts CategoryMapping + updates Merchant.default_category
  → next transaction from same merchant skips ML entirely (Stage 1 hit)

Every call to categorize() inserts a Transaction row and returns txn_id so the
confirm flow always has a valid record to update.
"""

from __future__ import annotations

import pickle
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
from sqlalchemy.orm import Session

from app.models import (
    Transaction, Merchant, CategoryMapping, UserFeedback,
    AuditLog, TxnType, MappingSource, FeedbackSource, ActorType,
)

CONFIDENCE_THRESHOLD = 0.85

# Canonical category list shared across all stages
CATEGORY_LABELS = [
    "Food & Dining", "Groceries", "Shopping", "Transport",
    "Entertainment", "Utilities", "Healthcare", "Finance",
    "Investments", "Travel", "Education", "Income", "Uncategorized",
]

# ── Rich label descriptions for sentence transformer ─────────────────────────
# Using detailed, keyword-rich descriptions dramatically improves cosine
# similarity — especially for receipt OCR text containing item names.
CATEGORY_DESCRIPTIONS = [
    # Food & Dining
    ("Food & Dining food restaurant meal order delivery dining eat takeout "
     "burger pizza biryani pasta sandwich wrap noodles rice curry dal paneer "
     "swiggy zomato dominos mcdonalds kfc subway cafe snack breakfast lunch dinner "
     "thali dessert ice cream coffee tea juice beverages hotel canteen"),
    # Groceries
    ("Groceries grocery supermarket vegetables fruits milk bread eggs butter "
     "cooking oil pulses flour sugar salt spices household items bigbasket blinkit "
     "reliance fresh dmart more supermarket nature basket fresh produce daily needs "
     "atta dal rice wheat provisions kirana store pantry"),
    # Shopping
    ("Shopping online shopping fashion clothing apparel shoes accessories "
     "electronics gadget mobile laptop tablet amazon flipkart myntra ajio meesho "
     "home decor furniture appliances cosmetics beauty jewellery gift stationery "
     "book sports equipment toys watch"),
    # Transport
    ("Transport travel commute cab ride auto rickshaw metro bus train fare "
     "uber ola rapido petrol diesel fuel HPCL BPCL Indian Oil pump parking "
     "toll highway fastag airport taxi vehicle maintenance servicing car bike"),
    # Entertainment
    ("Entertainment movies cinema streaming subscription OTT Netflix Amazon Prime "
     "Hotstar Disney Spotify Apple Music Gaana gaming PlayStation Xbox BookMyShow "
     "concerts events theme park bowling gaming arcade recreation hobby sport club"),
    # Utilities
    ("Utilities mobile recharge broadband internet electricity bill water bill "
     "gas cylinder LPG Jio Airtel BSNL Vi Vodafone postpaid prepaid DTH cable "
     "municipal tax property tax maintenance society charges pipe gas bill"),
    # Healthcare
    ("Healthcare medicine pharmacy doctor hospital consultation lab test "
     "diagnostic blood test X-ray MRI scan Apollo Practo 1mg Netmeds Medplus "
     "dentist physiotherapy health checkup health insurance premium vaccination "
     "surgery nursing home clinic wellness fitness gym yoga subscription"),
    # Finance
    ("Finance credit card bill payment EMI loan repayment insurance premium "
     "bank charges processing fee mortgage home loan personal loan car loan "
     "HDFC ICICI SBI Axis Kotak RBL bank transfer penalty interest payment debt"),
    # Investments
    ("Investments mutual fund SIP systematic investment plan stock equity "
     "shares demat Zerodha Groww Upstox Angel Broking HDFC Securities "
     "ELSS PPF NPS fixed deposit FD bond debenture gold ETF index fund NAV "
     "portfolio wealth management retirement corpus dividend"),
    # Travel
    ("Travel flight airline ticket hotel booking train IRCTC bus booking "
     "MakeMyTrip Goibibo Yatra EaseMyTrip OYO Airbnb holiday vacation "
     "resort trip tourism foreign exchange visa passport international domestic "
     "car rental luggage travel insurance package tour"),
    # Education
    ("Education school college university tuition fees course online learning "
     "Udemy Coursera edX BYJU's Unacademy Vedantu exam coaching entrance test "
     "books stationery library subscription certificate degree diploma "
     "professional development training workshop seminar"),
    # Income
    ("Income salary credit monthly income freelance payment consulting fee "
     "business revenue dividend interest earned bonus incentive reimbursement "
     "refund cashback reward rental income deposit received transfer received"),
    # Uncategorized
    "Uncategorized unknown miscellaneous other general expense transfer",
]

# ── Keyword rule lexicons  (Signal C — lexicon boost) ───────────────────────
KEYWORD_RULES: dict[str, list[str]] = {
    "Food & Dining": [
        "burger", "pizza", "biryani", "sandwich", "wrap", "noodles", "pasta",
        "rice", "curry", "dal", "paneer", "chicken", "fish", "veg", "non-veg",
        "meal", "snack", "breakfast", "lunch", "dinner", "thali", "dessert",
        "ice cream", "coffee", "tea", "juice", "beverage",
        "swiggy", "zomato", "dominos", "mcdonalds", "kfc", "subway",
        "restaurant", "cafe", "canteen", "dhaba", "takeout", "delivery",
    ],
    "Groceries": [
        "milk", "bread", "eggs", "butter", "vegetables", "fruits", "atta",
        "sugar", "salt", "oil", "flour", "masala", "spices",
        "bigbasket", "blinkit", "grofers", "zepto", "instamart", "dmart",
        "grocery", "kirana", "provisions",
    ],
    "Shopping": [
        "amazon", "flipkart", "myntra", "ajio", "meesho",
        "shirt", "jeans", "shoes", "dress", "clothing", "fashion", "apparel",
        "mobile", "laptop", "tablet", "headphones", "electronics",
        "watch", "jewellery", "cosmetics", "beauty", "furniture",
    ],
    "Transport": [
        "uber", "ola", "rapido", "auto", "cab", "taxi",
        "metro", "petrol", "diesel", "fuel", "fastag", "toll", "parking",
        "hpcl", "bpcl",
    ],
    "Entertainment": [
        "netflix", "prime", "hotstar", "disney", "spotify",
        "gaming", "xbox", "playstation", "bookmyshow", "movies", "cinema",
    ],
    "Utilities": [
        "recharge", "broadband", "electricity", "water bill", "gas", "lpg",
        "jio", "airtel", "bsnl", "vodafone", "dth", "prepaid", "postpaid",
    ],
    "Healthcare": [
        "medicine", "pharmacy", "doctor", "hospital", "clinic",
        "apollo", "practo", "1mg", "netmeds", "medplus", "lab", "blood test",
    ],
    "Finance": [
        "credit card", "emi", "loan", "insurance", "premium",
        "hdfc", "icici", "sbi", "axis", "kotak",
    ],
    "Investments": [
        "mutual fund", "sip", "stocks", "equity", "zerodha", "groww",
        "nps", "ppf", "fd", "fixed deposit",
    ],
    "Travel": [
        "flight", "airline", "hotel", "irctc", "makemytrip", "goibibo",
        "oyo", "airbnb", "holiday", "vacation", "resort",
    ],
    "Education": [
        "udemy", "coursera", "byju", "unacademy", "vedantu",
        "tuition", "school fee", "college fee", "exam",
    ],
    "Income": [
        "salary", "income", "dividend", "refund", "cashback", "bonus",
    ],
}

# ── Lazy model singletons ────────────────────────────────────────────────────
_sentence_model   = None
_label_embeddings = None
_svc_model        = None
_gb_model         = None   # HistGradientBoostingClassifier (Option A)
_gb_label_enc     = None   # sklearn LabelEncoder
_gb_trained_at    = None   # datetime of last successful training


def _get_sentence_model():
    global _sentence_model, _label_embeddings
    if _sentence_model is None:
        from sentence_transformers import SentenceTransformer
        _sentence_model   = SentenceTransformer("all-MiniLM-L6-v2")
        # Encode rich descriptions, not bare label names
        _label_embeddings = _sentence_model.encode(
            CATEGORY_DESCRIPTIONS, show_progress_bar=False, normalize_embeddings=True
        )
    return _sentence_model, _label_embeddings


def _get_svc_model():
    global _svc_model
    if _svc_model is None:
        from ml_models.categorization_model.model import CategorizationModel
        _svc_model = CategorizationModel()
        if _svc_model.is_trained():
            _svc_model.load()
    return _svc_model


# ── Merchant name normalisation ──────────────────────────────────────────────
_NOISE_WORDS = re.compile(
    r'\b(order|payment|txn|ref|upi|neft|imps|bill|purchase|pos'
    r'|pvt|ltd|llp|inc|corp|limited|private|india|online|pay|app'
    r'|technologies|technology|tech|services|service|solutions|solution'
    r'|enterprises|enterprise|foods|food|systems|system|networks|network'
    r'|communications|communication|internet|digital|global|group'
    r'|#\d+|\d{4,})\b',
    re.IGNORECASE,
)

def normalize_merchant(name: str) -> str:
    """
    Lowercase, strip corporate suffixes, noise tokens and numbers, collapse spaces.
    'SWIGGY INDIA PVT LTD ORDER 8823 UPI' → 'swiggy'
    'NETFLIX INDIA PVT LTD' → 'netflix'
    """
    if not name:
        return ""
    s = name.lower()
    s = _NOISE_WORDS.sub("", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:100]


# ── Core Service ─────────────────────────────────────────────────────────────

class CategorizationService:
    """
    Stateless service — pass a SQLAlchemy Session on every call.
    """

    # ── Public: categorize + insert ──────────────────────────────────────────

    def categorize(
        self,
        db: Session,
        user_id: int,
        raw_description: str,
        merchant_name: str,
        amount: float,
        txn_type: str = "debit",
        payment_mode: str = "UPI",
        account_id: int = 1,
        insert_to_db: bool = True,
        receipt_items: str = "",      # space-joined item text (backward compat)
        items: list[str] | None = None,  # structured item list for per-item embedding
    ) -> dict:
        """
        Run 4-stage pipeline.
        Always inserts a Transaction to DB (unless insert_to_db=False).
        Returns: category, subcategory, confidence, needs_confirmation,
                 pipeline_step, probabilities, txn_id, merchant_id
        """
        norm = normalize_merchant(merchant_name or raw_description)

        # ── Stage 1: DB lookup ────────────────────────────────────────────
        result = self._stage1_db(db, user_id, norm)

        # ── Stage 2: Multi-signal NLP + Gradient Boost fallback ────────────
        if result is None:
            result = self._stage2_nlp(
                raw_description, merchant_name, amount,
                txn_type, payment_mode,
                receipt_items=receipt_items,
                items=items or [],
                db=db,
                user_id=user_id,
            )

        # ── Insert transaction + resolve merchant ──────────────────────────
        txn_id = None
        merchant_id = result.pop("merchant_id", None)

        if insert_to_db:
            txn, mid = self._insert_transaction(
                db, user_id, account_id, amount, txn_type,
                raw_description, merchant_name, payment_mode,
                result["category"], result.get("subcategory", ""),
                result["confidence"], norm, merchant_id,
            )
            txn_id     = txn.txn_id if txn else None
            merchant_id = mid

        result["txn_id"]     = txn_id
        result["merchant_id"] = merchant_id
        return result

    # ── Public: confirm feedback (the critical feedback loop) ────────────────

    def confirm_category(
        self,
        db: Session,
        txn_id: int,
        corrected_category: str,
        corrected_subcategory: str = "",
        user_id: Optional[int] = None,
    ) -> dict:
        """
        Immediately:
          1. Update transaction.category
          2. Upsert CategoryMapping (so Stage 1 hits on next call)
          3. Update Merchant.default_category
          4. Save UserFeedback
          5. Audit log
        """
        txn = db.query(Transaction).filter(Transaction.txn_id == txn_id).first()
        if not txn:
            raise ValueError(f"Transaction {txn_id} not found")

        uid = user_id or txn.user_id
        old_cat = txn.category

        # 1. Update transaction
        txn.category    = corrected_category
        txn.subcategory = corrected_subcategory
        txn.user_verified = True

        # 2. Upsert CategoryMapping (most important — feedback loop)
        if txn.merchant_id:
            self._upsert_mapping(db, uid, txn.merchant_id,
                                 corrected_category, corrected_subcategory)

            # 3. Update global merchant default too
            merchant = db.query(Merchant).filter(
                Merchant.merchant_id == txn.merchant_id
            ).first()
            if merchant:
                merchant.default_category = corrected_category

        # 4. Save UserFeedback (upsert — unique on txn_id)
        existing_fb = db.query(UserFeedback).filter(
            UserFeedback.txn_id == txn_id
        ).first()
        if existing_fb:
            existing_fb.corrected_category    = corrected_category
            existing_fb.corrected_subcategory = corrected_subcategory
        else:
            db.add(UserFeedback(
                txn_id                = txn_id,
                corrected_category    = corrected_category,
                corrected_subcategory = corrected_subcategory,
                source                = FeedbackSource.USER_UI,
            ))

        # 5. Audit log
        db.add(AuditLog(
            actor_id      = uid,
            actor_type    = ActorType.USER,
            action        = "CONFIRM_CATEGORY",
            resource_type = "transaction",
            resource_id   = txn_id,
            old_value     = {"category": old_cat},
            new_value     = {"category": corrected_category},
        ))

        db.commit()
        return {
            "success":       True,
            "txn_id":        txn_id,
            "old_category":  old_cat,
            "new_category":  corrected_category,
            "merchant_id":   txn.merchant_id,
        }

    # ── Stage 1: DB merchant + user mapping ──────────────────────────────────

    def _stage1_db(
        self, db: Session, user_id: int, norm_merchant: str
    ) -> Optional[dict]:
        if not norm_merchant or len(norm_merchant) < 2:
            return None

        merchant = self._find_merchant(db, norm_merchant)
        if not merchant:
            return None

        # User-specific mapping takes highest priority
        user_map = db.query(CategoryMapping).filter(
            CategoryMapping.user_id    == user_id,
            CategoryMapping.merchant_id == merchant.merchant_id,
        ).first()

        if user_map:
            return {
                "category":           user_map.category,
                "subcategory":        user_map.subcategory or "",
                "confidence":         1.0,
                "needs_confirmation": False,
                "pipeline_step":      "user_feedback_db",
                "probabilities":      {},
                "merchant_id":        merchant.merchant_id,
            }

        # Global merchant default
        if merchant.default_category:
            return {
                "category":           merchant.default_category,
                "subcategory":        "",
                "confidence":         0.96,
                "needs_confirmation": False,
                "pipeline_step":      "merchant_cache_db",
                "probabilities":      {},
                "merchant_id":        merchant.merchant_id,
            }

        return None

    def _find_merchant(self, db: Session, norm: str) -> Optional[Merchant]:
        """
        Multi-pass merchant resolution:
        1. Exact ilike match on full norm string
        2. Each word (longest first) as a partial ilike match
        3. Raw substring scan on all merchants (in-memory, only when DB is small)
        """
        if not norm:
            return None

        # Pass 1: exact
        m = db.query(Merchant).filter(Merchant.clean_name.ilike(norm)).first()
        if m:
            return m

        # Pass 2: try every word, longest first (avoids short noise words matching)
        words = sorted(set(norm.split()), key=len, reverse=True)
        for word in words:
            if len(word) < 3:
                continue
            m = db.query(Merchant).filter(
                Merchant.clean_name.ilike(f"%{word}%")
            ).first()
            if m:
                return m

        # Pass 3: in-memory token overlap (catches phonetic near-matches)
        all_merchants = db.query(Merchant).all()
        norm_tokens = set(norm.split())
        best_m, best_overlap = None, 0
        for candidate in all_merchants:
            cand_tokens = set(candidate.clean_name.lower().split())
            overlap = len(norm_tokens & cand_tokens)
            if overlap > best_overlap:
                best_overlap = overlap
                best_m = candidate
        if best_overlap >= 1 and best_m:
            return best_m

        return None

    # ── Stage 2: NLP (SentenceTransformer primary, SVC secondary) ────────────

    def _stage2_nlp(
        self,
        raw_description: str,
        merchant_name: str,
        amount: float,
        txn_type: str,
        payment_mode: str,
        receipt_items: str = "",
        items: list[str] | None = None,
        db: Session | None = None,
        user_id: int | None = None,
    ) -> dict:
        """
        Multi-signal NLP classification.

        Signal A — Item-level embedding aggregate
          Each receipt item is encoded independently; votes are weighted by
          per-item peak confidence so high-clarity items dominate.

        Signal B — Full-text semantic similarity
          All text (items + merchant + description) is joined and compared
          against rich CATEGORY_DESCRIPTIONS via cosine similarity.

        Signal C — Keyword rule boost
          Lightweight lexicon match; adds a small additive score for strong
          keyword hits (e.g. "pizza" → Food & Dining).

        Signal D — User behavior prior
          User's most frequent verified category adds a weak prior signal
          to break near-ties consistently with their own history.

        Fallback — HistGradientBoostingClassifier (Option A)
          Embedding (384-dim) + tabular features trained on DB transactions.
          Lazy-trains on first call if ≥ 30 high-confidence samples exist.
        """
        items = items or []

        # ── A: Per-item embedding + confidence-weighted vote ──────────────
        if items:
            item_cat, item_score, item_probs = self._aggregate_item_votes(items)
        else:
            item_cat, item_score, item_probs = None, 0.0, {}

        # ── B: Full-text semantic similarity ──────────────────────────────
        query_text = " ".join(
            p for p in [" ".join(items), receipt_items, merchant_name, raw_description] if p
        ).strip()
        text_cat, text_score, text_probs = self._run_sentence_transformer(query_text)

        # ── C: Keyword boost ──────────────────────────────────────────────
        boost_text = " ".join(filter(None, [" ".join(items), receipt_items, merchant_name, raw_description]))
        boost_cat, boost_score = self._keyword_boost(boost_text)

        # ── D: User behavior prior ────────────────────────────────────────
        prior_cat, prior_weight = (
            self._user_behavior_prior(db, user_id) if db and user_id else (None, 0.0)
        )

        # ── Weighted vote ─────────────────────────────────────────────────
        # Item embeddings get more weight when present (most precise signal)
        W_ITEM  = 0.45 if items else 0.0
        W_TEXT  = 0.30 if items else 0.55
        W_KEY   = min(boost_score, 0.20)   # keyword boost capped at 0.20
        W_PRIOR = prior_weight             # typically 0.12

        scores: dict[str, float] = {cat: 0.0 for cat in CATEGORY_LABELS}
        if items and item_probs:
            for cat, s in item_probs.items():
                scores[cat] += s * W_ITEM
        for cat, s in text_probs.items():
            scores[cat] += s * W_TEXT
        if boost_cat:
            scores[boost_cat] += W_KEY
        if prior_cat:
            scores[prior_cat] += W_PRIOR

        total = sum(scores.values())
        if total > 0:
            scores = {k: round(v / total, 4) for k, v in scores.items()}

        best_cat  = max(scores, key=scores.get)
        best_conf = scores[best_cat]

        if best_conf >= CONFIDENCE_THRESHOLD:
            return {
                "category":           best_cat,
                "subcategory":        "",
                "confidence":         best_conf,
                "needs_confirmation": False,
                "pipeline_step":      "multi_signal_nlp",
                "probabilities":      scores,
            }

        # ── Gradient-boost fallback (Option A) ────────────────────────────
        gb_cat, gb_conf, gb_probs = self._stage3_gradient_boost(
            query_text, amount, txn_type, payment_mode, db
        )
        if gb_conf > best_conf:
            best_cat, best_conf, scores, step = gb_cat, gb_conf, gb_probs, "gradient_boost"
        else:
            step = "multi_signal_nlp"

        return {
            "category":           best_cat,
            "subcategory":        "",
            "confidence":         best_conf,
            "needs_confirmation": best_conf < CONFIDENCE_THRESHOLD,
            "pipeline_step":      step,
            "probabilities":      scores,
        }

    def _run_sentence_transformer(self, query: str) -> tuple[str, float, dict]:
        try:
            model, label_embs = _get_sentence_model()
            # normalize_embeddings=True → embeddings are unit vectors,
            # so np.dot == cosine similarity in [−1, 1]
            q_emb = model.encode(
                [query], show_progress_bar=False, normalize_embeddings=True
            )
            sims  = np.dot(q_emb, label_embs.T)[0]   # shape: (n_labels,)
            sims  = (sims + 1) / 2                    # rescale to [0, 1]
            idx   = int(np.argmax(sims))
            probs = dict(zip(CATEGORY_LABELS, [round(float(s), 4) for s in sims]))
            return CATEGORY_LABELS[idx], float(sims[idx]), probs
        except Exception:
            return "Uncategorized", 0.0, {}

    def _aggregate_item_votes(self, items: list[str]) -> tuple[str, float, dict]:
        """
        Step 2: Item-Level Embedding.
        Encode each receipt item independently (single batch forward pass),
        then combine via confidence-weighted vote.
        Items with a clear dominant category (high peak similarity) carry more
        weight than ambiguous items.
        """
        try:
            model, label_embs = _get_sentence_model()
            item_embs = model.encode(
                items, show_progress_bar=False, normalize_embeddings=True, batch_size=32
            )  # (n_items, embed_dim)

            sims = np.dot(item_embs, label_embs.T)  # (n_items, n_labels)
            sims = (sims + 1) / 2                    # rescale cosine to [0, 1]

            # Weight each item by its peak similarity (high-clarity items vote more)
            item_weights = sims.max(axis=1)          # (n_items,)
            w_sum = item_weights.sum()
            item_weights = (
                item_weights / w_sum if w_sum > 0 else np.ones(len(items)) / len(items)
            )

            agg_sims = np.dot(item_weights, sims)    # (n_labels,)
            idx      = int(np.argmax(agg_sims))
            probs    = {cat: round(float(s), 4) for cat, s in zip(CATEGORY_LABELS, agg_sims)}
            return CATEGORY_LABELS[idx], float(agg_sims[idx]), probs
        except Exception:
            return "Uncategorized", 0.0, {}

    def _keyword_boost(self, text: str) -> tuple[str | None, float]:
        """
        Signal C: Lexicon matching.
        Count keyword hits per category; return (top_category, boost_score ∈ [0, 0.20]).
        """
        text_lower = text.lower()
        hit_counts: dict[str, int] = {}
        for cat, keywords in KEYWORD_RULES.items():
            hits = sum(1 for kw in keywords if kw in text_lower)
            if hits:
                hit_counts[cat] = hits
        if not hit_counts:
            return None, 0.0
        best  = max(hit_counts, key=hit_counts.get)
        score = min(hit_counts[best] / max(len(KEYWORD_RULES[best]), 1) * 3.0, 0.20)
        return best, round(score, 4)

    def _user_behavior_prior(self, db: Session, user_id: int) -> tuple[str | None, float]:
        """
        Signal D: User behavior prior.
        Returns user's most frequent verified category as a weak signal (weight=0.12).
        Breaks near-ties consistently with the user's own spending history.
        """
        try:
            from sqlalchemy import func as sql_func
            row = (
                db.query(Transaction.category, sql_func.count(Transaction.txn_id).label("cnt"))
                .filter(
                    Transaction.user_id == user_id,
                    Transaction.user_verified == True,
                    Transaction.category != "Uncategorized",
                )
                .group_by(Transaction.category)
                .order_by(sql_func.count(Transaction.txn_id).desc())
                .first()
            )
            if row and row.category:
                return row.category, 0.12
        except Exception:
            pass
        return None, 0.0

    def _run_svc(
        self, raw_desc: str, amount: float, txn_type: str, payment_mode: str
    ) -> tuple[str, float, dict]:
        try:
            import pandas as pd
            svc = _get_svc_model()
            if svc is None or not svc._fitted:
                return "Uncategorized", 0.0, {}
            row = pd.DataFrame([{
                "text_input":   raw_desc,
                "amount":       amount,
                "txn_type":     txn_type,
                "payment_mode": payment_mode,
                "month": 1, "day_of_week": 0, "hour": 12, "is_recurring": 0,
            }])
            X     = svc.preprocessor.transform(row)
            proba = svc.classifier.predict_proba(X)[0]
            idx   = int(np.argmax(proba))
            probs = dict(zip(svc.label_classes, proba.tolist()))
            return svc.label_classes[idx], float(proba[idx]), probs
        except Exception:
            return "Uncategorized", 0.0, {}

    # ── Stage 3: Option A — Gradient Boost (embedding + tabular) ─────────────

    def _stage3_gradient_boost(
        self,
        query: str,
        amount: float,
        txn_type: str,
        payment_mode: str,
        db: Optional[Session] = None,
    ) -> tuple[str, float, dict]:
        """
        HistGradientBoostingClassifier (sklearn, XGBoost-equivalent algorithm).
        Features: sentence embedding (384-dim) + [log_amount, payment_mode, txn_type, hour].
        Lazy-trains from high-confidence DB transactions on first call.
        Falls back to LinearSVC if fewer than 30 training samples are available.
        """
        global _gb_model, _gb_label_enc

        if _gb_model is None and db is not None:
            self._train_gradient_boost(db)

        if _gb_model is None:
            return self._run_svc(query, amount, txn_type, payment_mode)

        try:
            st_model, _ = _get_sentence_model()
            emb = st_model.encode(
                [query], show_progress_bar=False, normalize_embeddings=True
            )[0]  # (384,)

            _PM    = ["UPI", "NEFT", "IMPS", "Card", "OCR", "Cash", "Other"]
            pm_enc = _PM.index(payment_mode) / len(_PM) if payment_mode in _PM else 1.0
            tt_enc = 0.0 if txn_type == "debit" else 1.0
            hour   = datetime.utcnow().hour / 24.0

            tab      = np.array([np.log1p(float(amount)), pm_enc, tt_enc, hour], dtype=np.float32)
            features = np.concatenate([emb, tab]).reshape(1, -1)   # (1, 388)

            proba   = _gb_model.predict_proba(features)[0]
            classes = _gb_label_enc.classes_
            idx     = int(np.argmax(proba))
            probs   = {c: round(float(p), 4) for c, p in zip(classes, proba)}
            return classes[idx], float(proba[idx]), probs
        except Exception:
            return self._run_svc(query, amount, txn_type, payment_mode)

    def _train_gradient_boost(self, db: Session) -> bool:
        """
        Train HistGradientBoostingClassifier on:
          - Sentence embeddings of transaction descriptions (384-dim)
          - Tabular: log(amount), payment_mode, txn_type, hour
        Sources: user-verified transactions OR confidence >= 0.85.
        Requires ≥ 30 samples. Saves artifact to
          ml_models/categorization_model/artifacts/gb_model.pkl.
        Auto-loads from disk on subsequent server restarts.
        """
        global _gb_model, _gb_label_enc, _gb_trained_at
        try:
            from sklearn.ensemble import HistGradientBoostingClassifier
            from sklearn.preprocessing import LabelEncoder

            artifact_path = Path("ml_models/categorization_model/artifacts/gb_model.pkl")

            # Load existing artifact rather than retraining on every cold start
            if artifact_path.exists() and _gb_trained_at is None:
                with open(artifact_path, "rb") as f:
                    saved = pickle.load(f)
                _gb_model      = saved["model"]
                _gb_label_enc  = saved["label_enc"]
                _gb_trained_at = saved.get("trained_at", datetime.utcnow())
                return True

            txns = (
                db.query(Transaction)
                .filter(
                    (Transaction.user_verified == True) |
                    (Transaction.confidence_score >= 0.85),
                    Transaction.category.notin_(["Uncategorized"]),
                )
                .limit(5000)
                .all()
            )
            if len(txns) < 30:
                return False

            st_model, _ = _get_sentence_model()
            texts   = [t.raw_description or "" for t in txns]
            labels  = [t.category for t in txns]
            amounts = [float(t.amount or 0) for t in txns]
            _PM     = ["UPI", "NEFT", "IMPS", "Card", "OCR", "Cash", "Other"]
            pm_enc  = [_PM.index(t.payment_mode) / len(_PM) if t.payment_mode in _PM else 1.0 for t in txns]
            tt_enc  = [0.0 if (t.txn_type and t.txn_type.value == "debit") else 1.0 for t in txns]

            embs = st_model.encode(
                texts, show_progress_bar=False, normalize_embeddings=True, batch_size=64
            )  # (N, 384)
            tab  = np.column_stack([
                np.log1p(amounts),
                pm_enc,
                tt_enc,
                [12.0 / 24.0] * len(txns),
            ])  # (N, 4)
            X = np.hstack([embs, tab]).astype(np.float32)   # (N, 388)

            le = LabelEncoder()
            y  = le.fit_transform(labels)

            clf = HistGradientBoostingClassifier(
                max_iter=150,
                max_depth=5,
                learning_rate=0.08,
                min_samples_leaf=3,
                random_state=42,
            )
            clf.fit(X, y)

            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            with open(artifact_path, "wb") as f:
                pickle.dump({"model": clf, "label_enc": le, "trained_at": datetime.utcnow()}, f)

            _gb_model      = clf
            _gb_label_enc  = le
            _gb_trained_at = datetime.utcnow()
            return True
        except Exception:
            return False

    # ── DB helpers ───────────────────────────────────────────────────────────

    def _insert_transaction(
        self,
        db: Session,
        user_id: int,
        account_id: int,
        amount: float,
        txn_type: str,
        raw_description: str,
        merchant_name: str,
        payment_mode: str,
        category: str,
        subcategory: str,
        confidence: float,
        norm_merchant: str,
        merchant_id: Optional[int],
    ) -> tuple[Optional[Transaction], Optional[int]]:
        try:
            # Find or create merchant
            merchant = None
            if merchant_id:
                merchant = db.query(Merchant).filter(
                    Merchant.merchant_id == merchant_id
                ).first()

            if not merchant and norm_merchant:
                merchant = self._find_merchant(db, norm_merchant)

            if not merchant:
                clean = norm_merchant[:255] or raw_description.split()[0][:50]
                merchant = Merchant(
                    raw_name         = (merchant_name or raw_description)[:500],
                    clean_name       = clean,
                    default_category = category,
                )
                db.add(merchant)
                db.flush()

            txn = Transaction(
                user_id          = user_id,
                account_id       = account_id,
                merchant_id      = merchant.merchant_id,
                amount           = amount,
                txn_type         = TxnType(txn_type),
                category         = category,
                subcategory      = subcategory,
                raw_description  = raw_description[:500],
                payment_mode     = payment_mode,
                user_verified    = False,
                confidence_score = confidence,
                txn_timestamp    = datetime.utcnow(),
            )
            db.add(txn)
            db.commit()
            db.refresh(txn)
            return txn, merchant.merchant_id
        except Exception as e:
            db.rollback()
            return None, None

    def _upsert_mapping(
        self,
        db: Session,
        user_id: int,
        merchant_id: int,
        category: str,
        subcategory: str,
    ) -> None:
        existing = db.query(CategoryMapping).filter(
            CategoryMapping.user_id     == user_id,
            CategoryMapping.merchant_id == merchant_id,
        ).first()
        if existing:
            existing.category    = category
            existing.subcategory = subcategory
            existing.confidence  = 1.0
            existing.updated_at  = datetime.utcnow()
        else:
            db.add(CategoryMapping(
                user_id     = user_id,
                merchant_id = merchant_id,
                category    = category,
                subcategory = subcategory,
                confidence  = 1.0,
                source      = MappingSource.USER,
            ))


def retrain_gradient_boost(db: Session) -> bool:
    """
    Public helper — call from router or scheduled job to force a fresh
    gradient-boost training run discarding any cached artifact.
    """
    global _gb_model, _gb_trained_at
    _gb_model      = None
    _gb_trained_at = None
    artifact = Path("ml_models/categorization_model/artifacts/gb_model.pkl")
    if artifact.exists():
        artifact.unlink()
    return categorization_service._train_gradient_boost(db)


# Singleton
categorization_service = CategorizationService()
