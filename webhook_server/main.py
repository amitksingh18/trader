#!/usr/bin/env python3
"""
TradingView -> Claude -> Telegram pipeline.

Flow:
  TradingView alert fires
    -> POSTs JSON to /webhook on this server
    -> claude_analysis.py asks Claude for reasoning on the setup
    -> telegram_notify.py sends the analysis to your phone
    -> journal.py logs the alert + analysis to a local CSV

This server never places orders. It only analyzes and notifies. If you decide
to act on a signal, you place the trade yourself in Groww/915 — that keeps a
human decision between every alert and real money moving, on purpose.
"""
import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request

from claude_analysis import analyze_alert
from groww_data import get_portfolio_context as get_groww_context
from journal import log_to_journal
from telegram_notify import send_telegram_message
from zerodha_data import get_portfolio_context as get_zerodha_context

load_dotenv(Path(__file__).parent / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("tv-webhook")

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")

app = FastAPI(title="TradingView Alert Analyzer")


@app.get("/")
def health_check():
    return {"status": "ok", "note": "Server is running. POST alerts to /webhook."}


@app.post("/webhook")
async def receive_alert(request: Request):
    payload = await request.json()
    logger.info("Received alert: %s", payload)

    if WEBHOOK_SECRET:
        if payload.get("secret") != WEBHOOK_SECRET:
            raise HTTPException(status_code=401, detail="Invalid or missing webhook secret")

    required = ("symbol", "price", "signal")
    missing = [field for field in required if field not in payload]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing required fields: {missing}")

    portfolio_contexts = {
        "groww": get_groww_context(payload["symbol"]),
        "zerodha": get_zerodha_context(payload["symbol"]),
    }
    analysis = analyze_alert(payload, portfolio_contexts)

    message = format_message(payload, analysis, portfolio_contexts)
    send_telegram_message(message)

    log_to_journal(payload, analysis)

    return {"status": "processed", "analysis": analysis}


def format_message(payload: dict, analysis: dict, portfolio_contexts: Optional[dict] = None) -> str:
    lines = [
        f"📊 {payload['symbol']} — {payload['signal'].upper()}",
        f"Price: {payload['price']}",
        "",
        f"Confidence: {analysis.get('confidence', 'N/A')}/10",
        f"Trend: {analysis.get('trend', 'N/A')}",
        f"Suggested stop-loss: {analysis.get('stop_loss', 'N/A')}",
        f"Suggested target: {analysis.get('target', 'N/A')}",
        "",
        analysis.get("reasoning", "No reasoning returned."),
        "",
    ]
    for broker, ctx in (portfolio_contexts or {}).items():
        if not ctx or not ctx.get("available"):
            continue
        if ctx.get("already_holding"):
            lines.append(f"📦 {broker.capitalize()}: you already hold this.")
        else:
            lines.append(f"📦 {broker.capitalize()}: you don't currently hold this.")
    lines.append("")
    lines.append("⚠️ This is analysis only. No order has been placed. Decide and trade manually.")
    return "\n".join(lines)


if __name__ == "__main__":
    import uvicorn

    # Render (and most cloud hosts) inject PORT — fall back to 8080 for local runs.
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=port == 8080)
