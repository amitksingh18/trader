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
  2. SMS: either buy a Twilio phone number (TWILIO_FROM_NUMBER), or set
     TWILIO_SMS_SENDER_ID to a text name like "TRADER" so the SMS shows a
     name instead of a number, like a company notification — see the
     Alphanumeric Sender ID note below, it needs its own registration.
  3. Calls: always need a real number — buy/use a Twilio number as
     TWILIO_FROM_NUMBER, alphanumeric sender IDs don't apply to calls.
  4. WhatsApp: join the Twilio WhatsApp sandbox (Console -> Messaging -> Try
     it out -> Send a WhatsApp message) to get TWILIO_WHATSAPP_FROM and
     activate your own number as the recipient.
  5. Put your own phone number in TWILIO_TO_NUMBER (E.164 format, e.g.
     +919876543210) — that's where the SMS, WhatsApp message, and call go.

Alphanumeric Sender ID (TWILIO_SMS_SENDER_ID): this is what makes an SMS
show up as "TRADER" instead of a phone number, the way companies send
notifications. It is NOT purely a code/env-var switch — Twilio requires
registering the sender ID, and in India it also requires DLT (Distributed
Ledger Technology) registration: a registered business entity, header, and
message template filed with a DLT platform (e.g. your telecom's portal),
which takes real-world days, not minutes. Unregistered alphanumeric SMS to
Indian numbers gets silently filtered by carriers. See
https://www.twilio.com/docs/sms/quickstart and
https://www.twilio.com/docs/sms/send-messages#alphanumeric-sender-id — this
code will use TWILIO_SMS_SENDER_ID as soon as it's set and registered.
"""
import logging
import os
from xml.sax.saxutils import escape

logger = logging.getLogger("tv-webhook")

ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
FROM_NUMBER = os.environ.get("TWILIO_FROM_NUMBER")
SMS_SENDER_ID = os.environ.get("TWILIO_SMS_SENDER_ID")
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
    sender = SMS_SENDER_ID or FROM_NUMBER
    if not (ACCOUNT_SID and AUTH_TOKEN and sender and TO_NUMBER):
        logger.warning("Twilio SMS not configured (need TWILIO_ACCOUNT_SID/"
                        "TWILIO_AUTH_TOKEN/TWILIO_TO_NUMBER, plus either "
                        "TWILIO_SMS_SENDER_ID or TWILIO_FROM_NUMBER). "
                        "Message would have been:\n%s", text)
        return

    try:
        _get_client().messages.create(body=text, from_=sender, to=TO_NUMBER)
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
