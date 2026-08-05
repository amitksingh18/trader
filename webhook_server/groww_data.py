"""Read-only Groww portfolio lookups — holdings and live price for a symbol.

Never places orders. Only used to give Claude real context (e.g. "you already
hold 10 shares of this at an average price of X") when analyzing an alert.

Uses the API key/secret auth flow (GROWW_API_KEY + GROWW_API_SECRET). Get
these from https://groww.in/trade-api/api-keys ("Generate API key"). Note:
these reset daily at 6 AM — need refreshing each trading day.

Note: as of Aug 2026 this also requires the calling server's IP to be
registered with Groww (see "Update static IP" on that same page) — this is
currently blocked for the Render deployment since Groww only allows editing
the registered IP once every 7 days. See docs/webhook_pipeline_setup.md.
"""
import logging
import os

from growwapi import GrowwAPI

logger = logging.getLogger("tv-webhook")

API_KEY = os.environ.get("GROWW_API_KEY")
API_SECRET = os.environ.get("GROWW_API_SECRET")

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    if not API_KEY or not API_SECRET:
        return None

    try:
        access_token = GrowwAPI.get_access_token(api_key=API_KEY, secret=API_SECRET)
        _client = GrowwAPI(access_token)
        return _client
    except Exception:
        logger.exception("Failed to authenticate with Groww API")
        return None


def get_portfolio_context(symbol: str) -> dict:
    """Returns holding info + live price for `symbol`, or a note that it's unavailable.

    Never raises — callers should treat this as best-effort context, not a
    required dependency (Claude analysis should still work if Groww is down
    or not configured).
    """
    client = _get_client()
    if client is None:
        return {"available": False, "note": "Groww API not configured"}

    try:
        holdings = client.get_holdings_for_user()
        matching = [
            h for h in holdings.get("holdings", holdings) if _symbol_matches(h, symbol)
        ]

        ltp = client.get_ltp(
            segment=client.SEGMENT_CASH,
            exchange_trading_symbols=(f"NSE_{symbol}",),
        )

        return {
            "available": True,
            "already_holding": bool(matching),
            "holding_detail": matching[0] if matching else None,
            "live_price": ltp,
        }
    except Exception:
        logger.exception("Groww portfolio lookup failed for %s", symbol)
        return {"available": False, "note": "Groww lookup failed — check logs"}


def _symbol_matches(holding: dict, symbol: str) -> bool:
    trading_symbol = holding.get("trading_symbol") or holding.get("tradingSymbol") or ""
    return trading_symbol.upper() == symbol.upper()
