"""Read-only Zerodha portfolio lookups — holdings, positions, and live price.

Never places orders. Only used to give Claude real context (e.g. "you already
hold 10 shares of this at an average price of X") when analyzing an alert.

Unlike Groww, Zerodha's access token requires a real browser login each
trading day — there's no key/secret-only flow. Run scripts/zerodha_login.py
locally each morning to generate ZERODHA_ACCESS_TOKEN, then set it here
(or in Render's Environment tab) before market open.
"""
import logging
import os

from kiteconnect import KiteConnect

logger = logging.getLogger("tv-webhook")

API_KEY = os.environ.get("ZERODHA_API_KEY")
ACCESS_TOKEN = os.environ.get("ZERODHA_ACCESS_TOKEN")

_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client

    if not API_KEY or not ACCESS_TOKEN:
        return None

    try:
        kite = KiteConnect(api_key=API_KEY)
        kite.set_access_token(ACCESS_TOKEN)
        _client = kite
        return _client
    except Exception:
        logger.exception("Failed to authenticate with Zerodha Kite API")
        return None


def get_portfolio_context(symbol: str) -> dict:
    """Returns holding/position info + live price for `symbol`, or a note
    that it's unavailable.

    Never raises — callers should treat this as best-effort context, not a
    required dependency (Claude analysis should still work if Zerodha is
    down, not configured, or today's access token expired).
    """
    client = _get_client()
    if client is None:
        return {"available": False, "note": "Zerodha API not configured"}

    try:
        holdings = client.holdings()
        matching_holdings = [h for h in holdings if h.get("tradingsymbol", "").upper() == symbol.upper()]

        positions = client.positions().get("net", [])
        matching_positions = [p for p in positions if p.get("tradingsymbol", "").upper() == symbol.upper()]

        ltp_data = client.ltp(f"NSE:{symbol}")
        live_price = ltp_data.get(f"NSE:{symbol}", {}).get("last_price")

        return {
            "available": True,
            "already_holding": bool(matching_holdings) or bool(matching_positions),
            "holding_detail": matching_holdings[0] if matching_holdings else None,
            "position_detail": matching_positions[0] if matching_positions else None,
            "live_price": live_price,
        }
    except Exception:
        logger.exception("Zerodha portfolio lookup failed for %s", symbol)
        return {"available": False, "note": "Zerodha lookup failed — check logs (access token may have expired)"}
