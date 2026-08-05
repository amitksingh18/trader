#!/usr/bin/env python3
"""Upserts one position/holding row into the 'Positions Log' worksheet.

One row per live position — repeated calls for the same (platform, symbol)
UPDATE that row in place (refreshing last_updated_ist + current numbers)
instead of piling up new rows. Once a position's status flips to "closed",
that row becomes a permanent historical record: a later call for the same
symbol (a fresh new trade) creates a NEW row rather than overwriting it,
since the match only looks at rows still in "open" status.

Usage:
  python3 append_position_log.py '{"platform": "Lemonn", "symbol": "NIFTY 04AUG 24500 CE", ...}'

Expected JSON keys (missing ones are left blank in the sheet):
  platform, symbol, exchange, product_type, side, quantity, avg_price,
  current_price, invested_value, current_value, pnl, pnl_pct, status

Reads Google service account credentials the same way webhook_server does,
but from a local file path (GOOGLE_SERVICE_ACCOUNT_FILE) rather than an
inline JSON env var, since this runs on your Mac, not a cloud host.
"""
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

from dotenv import load_dotenv
import gspread

load_dotenv(Path(__file__).parent / ".env")

SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")

IST = timezone(timedelta(hours=5, minutes=30))

HEADERS = [
    "first_seen_ist", "last_updated_ist", "platform", "symbol", "exchange",
    "product_type", "side", "quantity", "avg_price", "current_price",
    "invested_value", "current_value", "pnl", "pnl_pct", "status",
]
DATA_FIELDS = HEADERS[2:]  # everything except the two timestamp columns


def main():
    if not SERVICE_ACCOUNT_FILE or not SHEET_ID:
        sys.exit("Missing GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SHEET_ID in scripts/.env")

    if len(sys.argv) != 2:
        sys.exit("Usage: python3 append_position_log.py '<json row data>'")

    data = json.loads(sys.argv[1])
    platform = data.get("platform", "")
    symbol = data.get("symbol", "")

    client = gspread.service_account(filename=SERVICE_ACCOUNT_FILE)
    worksheet = client.open_by_key(SHEET_ID).worksheet("Positions Log")

    all_values = worksheet.get_all_values()
    header_row = all_values[0] if all_values else []
    if header_row != HEADERS:
        # Sheet has the old schema (or is empty) — reset the header row.
        worksheet.update(values=[HEADERS], range_name="A1")
        all_values = [HEADERS] + all_values[1:] if all_values else [HEADERS]

    now = datetime.now(IST).isoformat()

    # Look for an existing row for this platform+symbol that's still "open".
    match_row_index = None
    first_seen = now
    for i, row in enumerate(all_values[1:], start=2):  # sheet row numbers start at 2
        if len(row) < len(HEADERS):
            row = row + [""] * (len(HEADERS) - len(row))
        if row[2] == platform and row[3] == symbol and row[14] == "open":
            match_row_index = i
            first_seen = row[0] or now
            break

    new_row = [first_seen, now] + [str(data.get(f, "")) for f in DATA_FIELDS]

    if match_row_index:
        worksheet.update(values=[new_row], range_name=f"A{match_row_index}:O{match_row_index}")
        print(f"Updated existing row: {platform} / {symbol} (row {match_row_index})")
    else:
        worksheet.append_row(new_row)
        print(f"Inserted new row: {platform} / {symbol}")


if __name__ == "__main__":
    main()
