"""
ai_projection_engine/llm/mistral_client.py
==========================================
Unified Mistral LLM client with three operating modes:

  1. Cloud API  — uses Mistral's hosted API (requires MISTRAL_API_KEY).
  2. Local      — routes to a local Ollama instance (MISTRAL_USE_LOCAL=True).
  3. Fallback   — template-based insight when no LLM is available.

STRICT output rules enforced via system prompt:
  • ₹ amounts only — no percentages, no probabilities
  • Plain language — no jargon
  • 3-4 sentences maximum
"""

from __future__ import annotations

import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

_SYSTEM_INSTRUCTION = (
    "You are a friendly personal finance advisor for everyday users. "
    "Rules you must follow strictly:\n"
    "- Use only ₹ amounts. Never use percentages or ratios.\n"
    "- No financial jargon. No technical terms.\n"
    "- Maximum 3-4 sentences.\n"
    "- Be warm, encouraging, and practical.\n"
    "- Mention specific category names and exact ₹ amounts from the data provided."
)


class MistralClient:
    """
    Wraps Mistral inference (cloud or local Ollama).
    Instantiated once per request; stateless.
    """

    def __init__(self) -> None:
        from server.core.config import settings

        self.use_local: bool = settings.MISTRAL_USE_LOCAL
        self.api_key: str = settings.MISTRAL_API_KEY
        self.model: str = settings.MISTRAL_MODEL
        self.local_url: str = settings.MISTRAL_LOCAL_URL
        self.local_model: str = settings.MISTRAL_LOCAL_MODEL
        self.timeout: float = 90.0

    # ── Public Method ──────────────────────────────────────────────────────────

    def generate(self, prompt: str, context: dict | None = None) -> str:
        """
        Generate a financial insight from *prompt*.
        *context* is the raw llm_payload dict used as fallback data source.
        Gracefully falls back to a template if the LLM call fails.
        """
        try:
            if self.use_local:
                result = self._generate_local(prompt)
                logger.info("Ollama response received (%d chars)", len(result))
                return result
            if self.api_key:
                return self._generate_api(prompt)
            logger.warning(
                "No MISTRAL_API_KEY set and MISTRAL_USE_LOCAL=False. "
                "Using template fallback."
            )
            return self._fallback(context or {})
        except Exception as exc:
            logger.error(
                "LLM generation failed (%s): %s — switching to rule-based fallback.",
                type(exc).__name__,
                exc,
            )
            return self._fallback(context or {})

    # ── Cloud API ──────────────────────────────────────────────────────────────

    def _generate_api(self, prompt: str) -> str:
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM_INSTRUCTION},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 220,
            "temperature": 0.4,
            "top_p": 0.95,
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()

    # ── Local Ollama ───────────────────────────────────────────────────────────

    def _generate_local(self, prompt: str) -> str:
        """Call a locally running Ollama instance."""
        url = f"{self.local_url}/api/generate"
        full_prompt = f"{_SYSTEM_INSTRUCTION}\n\n{prompt}"
        payload = {
            "model": self.local_model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": 0.4,
                "num_predict": 220,
            },
        }
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "").strip()

    # ── Template Fallback ──────────────────────────────────────────────────────

    def _fallback(self, context: dict) -> str:
        """
        Rule-based insight built directly from the context dict.
        Used when no LLM is reachable.  Never regex-parses prompt text.
        """
        extra       = float(context.get("extra_spent", 0.0) or 0.0)
        saving      = float(context.get("saving_potential", 0.0) or 0.0)
        bal_range   = context.get("projected_balance_range", [0.0, 0.0]) or [0.0, 0.0]
        bal_lo      = float(bal_range[0]) if len(bal_range) > 0 else 0.0
        bal_hi      = float(bal_range[1]) if len(bal_range) > 1 else bal_lo
        over_budget = context.get("over_budget_categories", []) or []
        top_cats    = context.get("top_categories", []) or []
        causes      = context.get("main_causes", []) or []
        depletion   = bool(context.get("depletion_risk", False))
        cur_bal     = float(context.get("current_balance", 0.0) or 0.0)
        spent       = float(context.get("spent_this_month", 0.0) or 0.0)

        parts: list[str] = []

        # Sentence 1 — spending snapshot
        if extra > 1000:
            cat_str = " and ".join(causes) if causes else "several categories"
            parts.append(
                f"Your spending is running about ₹{extra:,.0f} above the usual "
                f"mid-month level, driven mainly by {cat_str}."
            )
        elif spent > 0:
            cat_str = ", ".join(top_cats[:3]) if top_cats else "various categories"
            parts.append(
                f"You have spent ₹{spent:,.0f} so far this month, "
                f"with the most going to {cat_str}."
            )
        else:
            parts.append("Your spending activity this month is still building up.")

        # Sentence 2 — over-budget alert
        if over_budget:
            ob_str = ", ".join(over_budget[:3])
            parts.append(
                f"You have exceeded your usual budget in {ob_str} this month."
            )

        # Sentence 3 — balance projection / depletion risk
        if depletion and cur_bal > 0:
            parts.append(
                f"Your current balance of ₹{cur_bal:,.0f} may run short before "
                f"month end if spending continues at this pace — consider pausing "
                f"non-essential purchases."
            )
        elif bal_lo > 0 or bal_hi > 0:
            parts.append(
                f"By the end of the month, your balance is projected to be "
                f"between ₹{bal_lo:,.0f} and ₹{bal_hi:,.0f}."
            )

        # Sentence 4 — savings tip
        if saving > 200:
            tip_cat = (
                over_budget[0] if over_budget
                else (top_cats[0] if top_cats else "discretionary spending")
            )
            parts.append(
                f"Pulling back on {tip_cat} by around ₹{saving:,.0f} could "
                f"noticeably boost your end-of-month savings."
            )

        return " ".join(parts) if parts else (
            f"Your current balance is ₹{cur_bal:,.0f}. "
            "Keep tracking your daily expenses to stay on top of your finances."
        )
