#!/usr/bin/env python3
"""Read-only price check via Groww's official API. Places no orders.

Uses the TOTP auth flow (GROWW_TOTP_TOKEN + GROWW_TOTP_SECRET), which has
no expiry — unlike the API key/secret flow, this never needs daily
regeneration.
"""
import os
import sys
from pathlib import Path

import pyotp
from dotenv import load_dotenv
from growwapi import GrowwAPI

load_dotenv(Path(__file__).parent / ".env")

TOTP_TOKEN = os.environ.get("GROWW_TOTP_TOKEN")
TOTP_SECRET = os.environ.get("GROWW_TOTP_SECRET")

if not TOTP_TOKEN or not TOTP_SECRET:
    sys.exit(
        "Missing credentials. Set them in scripts/.env, e.g.:\n"
        "  GROWW_TOTP_TOKEN=...\n"
        "  GROWW_TOTP_SECRET=...\n"
        "Get these from https://groww.in/trade-api/api-keys "
        "(dropdown next to 'Generate API key' -> 'Generate TOTP token')"
    )

# NSE_NIFTY confirmed against Groww's docs. BSE_SENSEX is inferred from the
# same naming pattern and not shown in their examples — if it errors, check
# the exact symbol in Groww's instrument master before assuming the script is broken.
SYMBOLS = ("NSE_NIFTY", "BSE_SENSEX")

totp = pyotp.TOTP(TOTP_SECRET).now()
access_token = GrowwAPI.get_access_token(api_key=TOTP_TOKEN, totp=totp)
groww = GrowwAPI(access_token)

ltp = groww.get_ltp(segment=groww.SEGMENT_CASH, exchange_trading_symbols=SYMBOLS)

for symbol, price in ltp.items():
    print(f"{symbol}: {price}")
