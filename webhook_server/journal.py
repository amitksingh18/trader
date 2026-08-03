"""Logs every alert + Claude's analysis to a local CSV trade journal, and
also to Google Sheets if configured (see sheets_journal.py).

The CSV write always happens — it's the reliable record with zero setup.
The Google Sheets write is best-effort on top of that; if it's not
configured or fails, the CSV entry still exists.
"""
import csv
from datetime import datetime, timezone
from pathlib import Path

from sheets_journal import log_to_sheets

JOURNAL_PATH = Path(__file__).parent / "journal.csv"

FIELDNAMES = [
    "timestamp_utc",
    "symbol",
    "signal",
    "price",
    "trend",
    "confidence",
    "stop_loss",
    "target",
    "reasoning",
]


def log_to_journal(payload: dict, analysis: dict) -> None:
    is_new_file = not JOURNAL_PATH.exists()

    with open(JOURNAL_PATH, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if is_new_file:
            writer.writeheader()

        writer.writerow({
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "symbol": payload.get("symbol"),
            "signal": payload.get("signal"),
            "price": payload.get("price"),
            "trend": analysis.get("trend"),
            "confidence": analysis.get("confidence"),
            "stop_loss": analysis.get("stop_loss"),
            "target": analysis.get("target"),
            "reasoning": analysis.get("reasoning"),
        })

    log_to_sheets(payload, analysis)
