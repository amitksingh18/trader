"""Sends trading alerts over SMS, WhatsApp, and a spoken phone call via Twilio.

Note on "WhatsApp calls": no public API (Twilio included) lets a bot place a
native WhatsApp voice/video call — WhatsApp's Business API is messaging-only.
So "calling" here means a real phone call (PSTN) that reads the alert aloud
with text-to-speech, which is the closest actual equivalent.

Each of the three channels is configured and fails independently — set only
the env vars for the channel(s) you want, leave the rest blank. See
docs/webhook_pipeline_setup.md for full setup steps.

Setup:
  1. Sign up at https://www.twilio.com/try-twilio, grab Account SID + Auth
     Token from the console dashboard.
  2. SMS/calls: buy or use a trial Twilio phone number as TWILIO_FROM_NUMBER.
  3. WhatsApp: join the Twilio WhatsApp sandbox (Console -> Messaging -> Try
     it out -> Send a WhatsApp message) to get TWILIO_WHATSAPP_FROM and
     activate your own number as the recipient.
  4. Put your own phone number in TWILIO_TO_NUMBER (E.164 format, e.g.
     +919876543210) — that's where the SMS, WhatsApp message, and call go.
"""
import logging
import os
from xml.sax.saxutils import escape

logger = logging.getLogger("tv-webhook")

ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER")
WHATSAPP_FROM = os.environ.get("TWILIO_WHATSAPP_FROM")
TO_NUMBER = os.environ.get("TWILIO_TO_NUMBER")

_client = None


def _get_client():
    global _client
    if _client is None:
        from twilio.rest import Client

        _client = Client(ACCOUNT_SID, AUTH_TOKEN)
    return _client


def send_sms(text: str) -> None:
    if not (ACCOUNT_SID and AUTH_TOKEN and FROM_NUMBER and TO_NUMBER):
        logger.warning("Twilio SMS not configured (need TWILIO_ACCOUNT_SID/"
                        "TWILIO_AUTH_TOKEN/TWILIO_FROM_NUMBER/TWILIO_TO_NUMBER). "
                        "Message would have been:\n%s", text)
        return

    try:
        _get_client().messages.create(body=text, from_=FROM_NUMBER, to=TO_NUMBER)
    except Exception:
        logger.exception("Failed to send SMS via Twilio")


def send_whatsapp_message(text: str) -> None:
    if not (ACCOUNT_SID and AUTH_TOKEN and WHATSAPP_FROM and TO_NUMBER):
        logger.warning("Twilio WhatsApp not configured (need TWILIO_ACCOUNT_SID/"
                        "TWILIO_AUTH_TOKEN/TWILIO_WHATSAPP_FROM/TWILIO_TO_NUMBER). "
                        "Message would have been:\n%s", text)
        return

    try:
        _get_client().messages.create(
            body=text,
            from_=f"whatsapp:{WHATSAPP_FROM}",
            to=f"whatsapp:{TO_NUMBER}",
        )
    except Exception:
        logger.exception("Failed to send WhatsApp message via Twilio")


def make_call(spoken_text: str) -> None:
    """Places a real phone call and reads spoken_text aloud via TTS. Keep it
    short — this is a summary, not the full analysis (nobody wants a
    2-minute robot reading paragraphs at them)."""
    if not (ACCOUNT_SID and AUTH_TOKEN and FROM_NUMBER and TO_NUMBER):
        logger.warning("Twilio calling not configured (need TWILIO_ACCOUNT_SID/"
                        "TWILIO_AUTH_TOKEN/TWILIO_FROM_NUMBER/TWILIO_TO_NUMBER). "
                        "Call would have said:\n%s", spoken_text)
        return

    twiml = f"<Response><Say>{escape(spoken_text)}</Say></Response>"
    try:
        _get_client().calls.create(twiml=twiml, from_=FROM_NUMBER, to=TO_NUMBER)
    except Exception:
        logger.exception("Failed to place call via Twilio")
