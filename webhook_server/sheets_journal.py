"""Appends each alert + analysis as a row in a Google Sheet.

Best-effort only — never raises. If not configured, silently does nothing
and the local CSV journal (journal.py) remains the reliable record.

Setup (see docs/webhook_pipeline_setup.md):
  1. Create a Google Cloud service account, download its JSON key.
  2. Share your target Google Sheet with the service account's email
     (found inside the JSON key) as an Editor.
  3. Put the JSON key's full contents in GOOGLE_SERVICE_ACCOUNT_JSON and the
     sheet's ID (from its URL) in GOOGLE_SHEET_ID.
"""
import json
import logging
import os
from datetime import datetime, timezone

import gspread

logger = logging.getLogger("tv-webhook")

SERVICE_ACCOUNT_JSON = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
SHEET_ID = os.environ.get("GOOGLE_SHEET_ID")

_worksheet = None
_init_attempted = False


def _get_worksheet():
    global _worksheet, _init_attempted
    if _worksheet is not None or _init_attempted:
        return _worksheet

    _init_attempted = True

    if not SERVICE_ACCOUNT_JSON or not SHEET_ID:
        return None

    try:
        info = json.loads(SERVICE_ACCOUNT_JSON)
        client = gspread.service_account_from_dict(info)
        spreadsheet = client.open_by_key(SHEET_ID)
        _worksheet = spreadsheet.sheet1
        return _worksheet
    except Exception:
        logger.exception("Failed to connect to Google Sheets")
        return None


def log_to_sheets(payload: dict, analysis: dict) -> None:
    worksheet = _get_worksheet()
    if worksheet is None:
        return

    try:
        worksheet.append_row([
            datetime.now(timezone.utc).isoformat(),
            payload.get("symbol"),
            payload.get("signal"),
            payload.get("price"),
            analysis.get("trend"),
            analysis.get("confidence"),
            analysis.get("stop_loss"),
            analysis.get("target"),
            analysis.get("reasoning"),
        ])
    except Exception:
        logger.exception("Failed to append row to Google Sheets")
