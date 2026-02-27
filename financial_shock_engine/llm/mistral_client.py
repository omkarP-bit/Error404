"""
financial_shock_engine/llm/mistral_client.py
============================================
Mistral LLM client — identical pattern to ai_projection_engine.
Three modes: Local Ollama → Cloud API → Rule-based fallback.

The fallback ALWAYS uses the context dict directly (never regex-parses prompt text).
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_SYSTEM_INSTRUCTION = (
    "You are a friendly personal finance advisor explaining financial risk to everyday users.\n"
    "Rules:\n"
    "- Use only ₹ amounts. Never use percentages or ratios.\n"
    "- No financial jargon. Keep it plain and warm.\n"
    "- Maximum 3-4 sentences.\n"
    "- Be specific: mention categories by name, use exact ₹ amounts from the data.\n"
    "- Be encouraging and practical."
)


class MistralClient:
    def __init__(self) -> None:
        from configs import settings
        self.use_local:   bool  = settings.MISTRAL_USE_LOCAL
        self.api_key:     str   = settings.MISTRAL_API_KEY
        self.model:       str   = settings.MISTRAL_MODEL
        self.local_url:   str   = settings.MISTRAL_LOCAL_URL
        self.local_model: str   = settings.MISTRAL_LOCAL_MODEL
        self.timeout:     float = settings.MISTRAL_TIMEOUT

    # ── Public ────────────────────────────────────────────────────────────────

    def generate(self, prompt: str, context: dict | None = None) -> str:
        try:
            if self.use_local:
                result = self._generate_local(prompt)
                logger.info("Ollama response received (%d chars)", len(result))
                return result
            if self.api_key:
                return self._generate_api(prompt)
            logger.warning("No LLM configured — using rule-based fallback.")
            return self._fallback(context or {})
        except Exception as exc:
            logger.error(
                "LLM generation failed (%s): %s — using rule-based fallback.",
                type(exc).__name__, exc,
            )
            return self._fallback(context or {})

    # ── Cloud API ─────────────────────────────────────────────────────────────

    def _generate_api(self, prompt: str) -> str:
        url = "https://api.mistral.ai/v1/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_INSTRUCTION},
                {"role": "user",   "content": prompt},
            ],
            "max_tokens": 250,
            "temperature": 0.4,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                url,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

    # ── Local Ollama ──────────────────────────────────────────────────────────

    def _generate_local(self, prompt: str) -> str:
        url = f"{self.local_url}/api/generate"
        payload = {
            "model": self.local_model,
            "prompt": f"{_SYSTEM_INSTRUCTION}\n\n{prompt}",
            "stream": False,
            "options": {"temperature": 0.4, "num_predict": 250},
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()

    # ── Rule-based fallback ───────────────────────────────────────────────────

    def _fallback(self, context: dict) -> str:
        """Build a dynamic, data-driven insight from context dict. Never uses regex."""
        capacity       = float(context.get("shock_capacity", 0.0) or 0.0)
        safe_limit     = float(context.get("safe_shock_limit", 0.0) or 0.0)
        label          = context.get("resilience_label", "Moderate")
        cur_bal        = float(context.get("current_balance", 0.0) or 0.0)
        top_cats       = context.get("top_risk_categories", []) or []
        depletion      = bool(context.get("depletion_risk", False))
        savings        = float(context.get("total_monthly_saveable", 0.0) or 0.0)
        volatility     = float(context.get("expense_volatility", 0.0) or 0.0)

        parts: list[str] = []

        # Sentence 1 — headline
        if capacity > 10_000:
            parts.append(
                f"Your finances are in {label.lower()} shape — you can absorb an unexpected "
                f"expense of up to ₹{capacity:,.0f} this month without disrupting your goals."
            )
        elif capacity > 3_000:
            parts.append(
                f"Your current shock buffer is ₹{capacity:,.0f}, which means you have some "
                f"room for surprises, but large unexpected expenses could put you at risk."
            )
        else:
            parts.append(
                f"Your shock absorption capacity is low at ₹{capacity:,.0f} right now. "
                f"Any unexpected expense above ₹{safe_limit:,.0f} could strain your finances."
            )

        # Sentence 2 — risk category
        if top_cats:
            cat_str = " and ".join(top_cats[:2])
            if volatility > 0.4:
                parts.append(f"High spending variability in {cat_str} is the main factor reducing your resilience.")
            else:
                parts.append(f"Your highest spending areas are {cat_str}, which have the most room for adjustment.")

        # Sentence 3 — depletion / balance
        if depletion:
            parts.append(
                f"With a current balance of ₹{cur_bal:,.0f}, there is a risk of running short "
                f"before month end — consider pausing non-essential purchases."
            )
        elif cur_bal > 0:
            parts.append(
                f"Your current balance is ₹{cur_bal:,.0f}. Keeping it above ₹{safe_limit:,.0f} "
                f"gives you a comfortable safety net."
            )

        # Sentence 4 — savings action
        if savings > 500:
            parts.append(
                f"Trimming discretionary spending by ₹{savings:,.0f} this month would "
                f"meaningfully strengthen your shock resilience."
            )

        return " ".join(parts) if parts else (
            f"Your shock buffer stands at ₹{capacity:,.0f}. "
            "Monitor your discretionary categories to keep your resilience strong."
        )
