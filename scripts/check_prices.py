#!/usr/bin/env python3
"""Read-only price check via Groww's official API. Places no orders."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from growwapi import GrowwAPI

load_dotenv(Path(__file__).parent / ".env")

API_KEY = os.environ.get("GROWW_API_KEY")
API_SECRET = os.environ.get("GROWW_API_SECRET")

if not API_KEY or not API_SECRET:
    sys.exit(
        "Missing credentials. Set them in scripts/.env, e.g.:\n"
        "  GROWW_API_KEY=...\n"
        "  GROWW_API_SECRET=...\n"
        "Get these from https://groww.in/trade-api/api-keys "
        "(resets daily at 6 AM — needs refreshing each trading day)"
    )

# NSE_NIFTY confirmed against Groww's docs. BSE_SENSEX is inferred from the
# same naming pattern and not shown in their examples — if it errors, check
# the exact symbol in Groww's instrument master before assuming the script is broken.
SYMBOLS = ("NSE_NIFTY", "BSE_SENSEX")

access_token = GrowwAPI.get_access_token(api_key=API_KEY, secret=API_SECRET)
groww = GrowwAPI(access_token)

ltp = groww.get_ltp(segment=groww.SEGMENT_CASH, exchange_trading_symbols=SYMBOLS)

for symbol, price in ltp.items():
    print(f"{symbol}: {price}")
