#!/usr/bin/env python3
"""Daily Zerodha Kite Connect login — generates today's access token.

Zerodha's access tokens expire daily and require an actual browser login
each time (unlike Groww's plain key/secret). This script can't do the login
for you — you complete that yourself in your browser — it just handles the
token exchange once you have the request_token.

Usage:
  python3 zerodha_login.py
  (follow the printed URL, log in, paste back the request_token from the
  redirect URL when prompted)
"""
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from kiteconnect import KiteConnect

load_dotenv(Path(__file__).parent / ".env")

API_KEY = os.environ.get("ZERODHA_API_KEY")
API_SECRET = os.environ.get("ZERODHA_API_SECRET")

if not API_KEY or not API_SECRET:
    sys.exit(
        "Missing credentials. Set them in scripts/.env, e.g.:\n"
        "  ZERODHA_API_KEY=...\n"
        "  ZERODHA_API_SECRET=...\n"
        "Get these from https://developers.kite.trade/ (requires the paid "
        "Kite Connect subscription)."
    )

kite = KiteConnect(api_key=API_KEY)

print("1. Open this URL in your browser and log in to Zerodha:")
print(f"   {kite.login_url()}")
print()
print("2. After login, you'll be redirected to a URL like:")
print("   https://your-redirect-url/?request_token=XXXXXXXX&action=login&status=success")
print("   Copy just the request_token value.")
print()

request_token = input("Paste the request_token here: ").strip()

# Strip common paste artifacts (e.g. if the whole URL got pasted by mistake).
match = re.search(r"request_token=([^&\s]+)", request_token)
if match:
    request_token = match.group(1)

session = kite.generate_session(request_token, api_secret=API_SECRET)
access_token = session["access_token"]

# Save today's access token into .env for other scripts to use.
env_path = Path(__file__).parent / ".env"
lines = env_path.read_text().splitlines(keepends=True) if env_path.exists() else []
new_lines = []
found = False
for line in lines:
    if line.startswith("ZERODHA_ACCESS_TOKEN="):
        new_lines.append(f"ZERODHA_ACCESS_TOKEN={access_token}\n")
        found = True
    else:
        new_lines.append(line if line.endswith("\n") else line + "\n")
if not found:
    new_lines.append(f"ZERODHA_ACCESS_TOKEN={access_token}\n")
env_path.write_text("".join(new_lines))

print()
print("Access token saved to scripts/.env — valid until end of trading day.")
print(f"User: {session.get('user_name', 'unknown')}")
