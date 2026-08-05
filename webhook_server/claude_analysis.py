"""Sends the TradingView alert to Claude and gets back structured trade reasoning.

Uses the Anthropic API (a separate product from this chat session — you need
your own API key from https://console.anthropic.com/).
"""
import json
import logging
import os
import re
from typing import Optional

import anthropic

logger = logging.getLogger("tv-webhook")

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

MODEL = "claude-sonnet-5"

SYSTEM_PROMPT = """You are a trading analysis assistant. You are given a single \
TradingView alert (symbol, price, signal type, and any extra fields the trader \
included). Your job is only to REASON about the setup, in plain everyday language \
a beginner can follow — you do not place trades and you are not giving financial \
advice, just describing the technical picture.

Always respond with a JSON object with exactly these keys:
  "trend": one short phrase, e.g. "uptrend" / "downtrend" / "sideways/unclear"
  "confidence": integer 1-10, how clean/high-probability this setup looks technically
  "stop_loss": a suggested stop-loss price (number) or "N/A" if not enough info
  "target": a suggested target price (number) or "N/A" if not enough info
  "reasoning": 2-4 plain-language sentences explaining the why, no jargon without \
explanation, mentioning specific risks (e.g. proximity to expiry, weak volume, \
against-the-trend entry).

Return ONLY the JSON object, no other text."""


def analyze_alert(payload: dict, portfolio_contexts: Optional[dict] = None) -> dict:
    """portfolio_contexts: dict of {broker_name: context_dict}, e.g.
    {"groww": {...}, "zerodha": {...}} — each optional, each independently
    available or not."""
    user_message = (
        "Analyze this TradingView alert:\n"
        f"{json.dumps(payload, indent=2)}"
    )
    available_contexts = {
        broker: ctx for broker, ctx in (portfolio_contexts or {}).items()
        if ctx and ctx.get("available")
    }
    if available_contexts:
        user_message += (
            "\n\nReal portfolio context for this symbol (read-only, from the "
            "trader's actual broker accounts — factor this into your reasoning, "
            "e.g. whether this adds to an existing position, and note if the "
            "same symbol shows up differently across brokers):\n"
            f"{json.dumps(available_contexts, indent=2)}"
        )

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        text = response.content[0].text
        return _parse_json_response(text)
    except json.JSONDecodeError:
        logger.exception("Claude did not return valid JSON: %s", text)
        return _fallback_analysis("Claude response was not valid JSON.")
    except Exception:
        logger.exception("Claude API call failed")
        return _fallback_analysis("Claude API call failed — check ANTHROPIC_API_KEY and logs.")


def _parse_json_response(text: str) -> dict:
    """Claude sometimes wraps JSON in ```json fences despite instructions not
    to — strip those, then fall back to extracting the first {...} block."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)

    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", stripped, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _fallback_analysis(reason: str) -> dict:
    return {
        "trend": "unknown",
        "confidence": 0,
        "stop_loss": "N/A",
        "target": "N/A",
        "reasoning": reason,
    }
