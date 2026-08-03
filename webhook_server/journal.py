"""Logs every alert + Claude's analysis to a local CSV trade journal.

Starts as a plain CSV so there's zero extra setup (no API keys, no auth).
Open journal.csv directly in Excel/Numbers/Google Sheets any time.

To upgrade to live Google Sheets or Notion later: both need their own API
credentials (a Google service account, or a Notion integration token) — that's
a separate setup step, not something wired in by default here.
"""
import csv
from datetime import datetime, timezone
from pathlib import Path

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
