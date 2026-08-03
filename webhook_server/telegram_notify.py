"""Sends a message to your Telegram chat via a bot.

Setup (see docs/webhook_pipeline_setup.md for full steps):
  1. Message @BotFather on Telegram, /newbot, get a bot token.
  2. Message your new bot once (anything), then visit
     https://api.telegram.org/bot<TOKEN>/getUpdates to find your chat_id.
  3. Put both in .env as TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.
"""
import logging
import os

import httpx

logger = logging.getLogger("tv-webhook")

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")


def send_telegram_message(text: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        logger.warning("Telegram not configured (TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID missing). "
                        "Message would have been:\n%s", text)
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        response = httpx.post(url, json={"chat_id": CHAT_ID, "text": text}, timeout=10)
        response.raise_for_status()
    except Exception:
        logger.exception("Failed to send Telegram message")
