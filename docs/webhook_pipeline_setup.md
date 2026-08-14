# TradingView → Claude → Telegram alert pipeline — setup guide

What this does: a TradingView alert fires → hits your server → Claude reasons
about the setup → you get a Telegram message with its analysis → it's logged
to a CSV journal. **No orders are ever placed automatically.** You read the
analysis and decide manually, then trade on Groww/915 yourself.

## 1. Get an Anthropic API key

This is a *different* product from the Claude chat you're using now — it's a
developer key that lets code call Claude directly.

1. Go to https://console.anthropic.com/
2. Sign up / log in, add billing (pay-as-you-go, usually a few cents per alert)
3. Create an API key, copy it

## 2. Create a Telegram bot

1. Open Telegram, search for **@BotFather**, start a chat
2. Send `/newbot`, follow the prompts (give it any name/username)
3. BotFather gives you a **bot token** — copy it
4. Search for your new bot by its username, send it any message (e.g. "hi") —
   this lets it know your chat exists
5. In a browser, visit:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
   (replace `<YOUR_TOKEN>` with your real token)
6. Look for `"chat":{"id":123456789` in the response — that number is your
   **chat ID**

## 3. Configure the server

```bash
cd ~/Downloads/trader/webhook_server
cp .env.example .env
```

Open `.env` and fill in:
- `ANTHROPIC_API_KEY` — from step 1
- `TELEGRAM_BOT_TOKEN` — from step 2
- `TELEGRAM_CHAT_ID` — from step 2
- `WEBHOOK_SECRET` — make up any random string (e.g. `mySecret123`) — this
  stops randoms on the internet from triggering fake alerts on your server

## 4. Install dependencies and run

```bash
cd ~/Downloads/trader/webhook_server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

You should see `Uvicorn running on http://0.0.0.0:8080`. Leave this running.

## 5. Expose it to the internet (for testing)

TradingView needs a public URL to send alerts to — your laptop alone isn't
reachable from the internet. For testing, use **ngrok** (free):

```bash
brew install ngrok
ngrok http 8080
```

It'll print something like `https://abcd1234.ngrok-free.app` — that's your
public webhook base URL. Your webhook endpoint is:

```
https://abcd1234.ngrok-free.app/webhook
```

**Note:** free ngrok URLs change every time you restart it — fine for
testing, but for something you keep running long-term you'd eventually want
real hosting (Render, Railway, a small VPS). Not needed to get started.

## 6. Set up the TradingView alert

1. Open a chart on TradingView, add the `ma_crossover_alert.pine` script
   (paste it into Pine Editor → Add to chart)
2. Edit the script's `buyMsg`/`sellMsg` — replace `REPLACE_ME` with the same
   string you set as `WEBHOOK_SECRET` in `.env`
3. Click the alarm-clock icon → **Create Alert**
4. Condition: pick "MA Crossover Alert" → "Buy" or "Sell"
5. Under **Notifications**, toggle on **Webhook URL**, paste your ngrok
   webhook URL from step 5
6. Save the alert

## 7. Test it

Trigger a quick manual test without waiting for a real crossover:

```bash
curl -X POST http://localhost:8080/webhook \
  -H "Content-Type: application/json" \
  -d '{"symbol": "NIFTY", "price": 24700, "signal": "buy", "secret": "mySecret123"}'
```

(use your real `WEBHOOK_SECRET` value). You should see:
- A log line in the server terminal
- A Telegram message on your phone within a few seconds
- A new row in `webhook_server/journal.csv`

## 8. Optional: log every alert to Google Sheets

By default, alerts are logged to a local `journal.csv` file only. To also
have every alert appear as a row in a Google Sheet you can open from any
device:

1. Go to https://console.cloud.google.com/ → create a project (or use an
   existing one)
2. **APIs & Services → Library** → search "Google Sheets API" → **Enable**
3. **APIs & Services → Credentials** → **Create Credentials → Service
   Account** → give it any name → **Create and Continue** → skip the
   optional steps → **Done**
4. Click the new service account → **Keys** tab → **Add Key → Create new
   key → JSON** → downloads a `.json` file
5. Open that file — copy its **entire contents** as `GOOGLE_SERVICE_ACCOUNT_JSON`
   (in `.env`, this needs to be on one line — most editors can do "minify" or
   just leave the file's raw JSON as-is if your `.env` format allows multi-line
   values)
6. Inside that JSON file, find the `"client_email"` field — copy that email
   address
7. Create (or open) a Google Sheet, click **Share**, paste that service
   account email in, give it **Editor** access
8. Copy the Sheet's ID from its URL: `docs.google.com/spreadsheets/d/`**`THIS_PART`**`/edit`
   → that's `GOOGLE_SHEET_ID`
9. Add both env vars to `.env` (or Render's Environment tab)

Leave both blank to skip this — the local CSV journal keeps working
regardless, this is purely additive.

## 9. Optional: give Claude your real Groww holdings (read-only)

By default Claude only sees the alert itself (symbol, price, signal). You can
optionally let it also see whether you already hold that stock and its live
price from your actual Groww account — this is **read-only**, it never places
orders, just adds context like "you already hold 10 shares of this at ₹X."

1. Go to https://groww.in/trade-api/api-keys → click the dropdown next to
   "Generate API key" → **"Generate TOTP token"** → generate `GROWW_TOTP_TOKEN`
   / `GROWW_TOTP_SECRET`
2. Unlike the plain API key/secret flow, **TOTP credentials don't expire** —
   no daily regeneration needed
3. Add both to `.env` (or Render's Environment tab if deployed)
4. Leave them blank if you don't want this feature — the pipeline works fine
   without it, it just skips the portfolio context silently
5. **Known blocker as of Aug 2026:** Groww also requires the calling
   server's IP to be registered ("Update static IP" on the same page), and
   only lets you change that once every 7 days. Render's free tier doesn't
   have a fixed outbound IP, so this feature is currently non-functional
   when deployed — it does work if you run the check locally from your own
   machine (see `scripts/append_position_log.py`), since your home IP is
   already the registered one.

## 10. Optional: SMS, WhatsApp, and phone call alerts (Twilio)

By default alerts only go to Telegram. You can additionally get an SMS, a
WhatsApp message, and a real phone call (that reads the alert aloud) for
every signal, via [Twilio](https://www.twilio.com/try-twilio).

**Heads up:** there's no such thing as a bot placing a native WhatsApp voice
call — WhatsApp's Business API (which Twilio uses) is messaging-only, no
provider exposes that as an API. "Calling" here means an actual phone call
over the regular phone network, with the alert read out by text-to-speech —
that's the closest real equivalent, and arguably more useful for something
you want to notice immediately.

Each channel is independent — configure only the ones you want:

1. Sign up at https://www.twilio.com/try-twilio (free trial includes some
   credit). From the console dashboard, copy your **Account SID** and
   **Auth Token** into `.env` as `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN`.
2. **For SMS and phone calls:** get a Twilio phone number (trial accounts
   get one free) — Console → Phone Numbers → Buy a number. Put it in
   `TWILIO_FROM_NUMBER` (E.164 format, e.g. `+14155551234`).
3. **For WhatsApp:** Console → Messaging → Try it out → Send a WhatsApp
   message, join the sandbox by sending the given code to the given number
   from your own WhatsApp. Put the sandbox number in `TWILIO_WHATSAPP_FROM`.
4. Put your own phone number in `TWILIO_TO_NUMBER` (E.164, e.g.
   `+919876543210`) — SMS, WhatsApp, and the call all go here.
5. On a trial account, `TWILIO_TO_NUMBER` must first be verified in the
   Twilio console (Console → Phone Numbers → Verified Caller IDs) before
   Twilio will send to it.
6. Leave any of these blank to skip that channel — the pipeline logs a
   warning and carries on; Telegram and the CSV journal are unaffected.

### Making SMS show a name instead of your number

By default, `TWILIO_FROM_NUMBER` is what shows up as the sender — a phone
number. To have the SMS show a text name instead (e.g. `TRADER`), the way
a company's OTP/notification texts do, set `TWILIO_SMS_SENDER_ID` to that
name (3-11 letters/digits, no spaces) instead of relying on
`TWILIO_FROM_NUMBER`.

**This is not just an env var** — it needs real registration before it'll
actually deliver:

1. Register the Alphanumeric Sender ID with Twilio — Console → Messaging →
   Senders → Alphanumeric Sender IDs → Create new Sender ID. Approval can
   take a few hours to a few days depending on destination country.
2. **If texting Indian numbers:** India additionally requires **DLT
   (Distributed Ledger Technology) registration** — you (or your business)
   register as an entity on a DLT platform (e.g. your telecom operator's
   portal, or an aggregator like Twilio partners with), register the
   specific sender "header" (your chosen name) and the exact message
   template being sent, and get both approved. This is a multi-day
   real-world compliance process, not something achievable purely from
   this codebase — Twilio's guide:
   https://www.twilio.com/docs/sms/send-messages#india
3. Until that registration is complete and approved, Indian carriers
   silently drop unregistered alphanumeric SMS — you won't get an error,
   the message just never arrives. Leave `TWILIO_SMS_SENDER_ID` blank and
   the pipeline falls back to sending from `TWILIO_FROM_NUMBER` (a normal
   phone number) instead, which needs no such registration.

## 11. Optional: deploy to the cloud (no laptop needed)

Everything above runs on your own machine — if you close your laptop or lose
wifi, alerts stop working. To have it running all the time without babysitting
a laptop, deploy it to **Render** (free tier, no credit card required, ~750
free hours/month — more than enough for one small service running 24/7).

**One thing I can't do for you:** creating the Render/GitHub accounts. That
needs to be you, a couple minutes each, then the rest is mostly automatic.

1. **Push this project to GitHub** (skip if you already have a GitHub repo for it):
   ```bash
   cd ~/Downloads/trader
   git add .
   git commit -m "Add TradingView alert pipeline"
   ```
   Then create a new repo at https://github.com/new (call it e.g. `trader`),
   and follow GitHub's instructions to push your existing local repo to it.

2. **Sign up at https://render.com** (free, email or GitHub login — no card needed)

3. **New → Blueprint** → connect your GitHub repo → Render will read the
   `render.yaml` file already sitting in this project and auto-configure
   everything (build command, start command, Python runtime)

4. Render will prompt you to fill in the 4 secret values it sees are needed
   (`ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`,
   `WEBHOOK_SECRET`) — paste in the same values from your local `.env`

5. Click **Deploy** — Render gives you a permanent URL like
   `https://tv-alert-analyzer.onrender.com`

6. Update your TradingView alert's webhook URL to
   `https://tv-alert-analyzer.onrender.com/webhook` instead of the ngrok one

**Note:** the free tier sleeps after 15 minutes of no traffic, so the very
first alert after a quiet period takes ~10-30 seconds longer to respond while
it wakes up — after that it's instant again. Not an issue for this use case
since you're not trading on millisecond timing.

## What this pipeline does NOT do

- It does not place orders — Groww/broker execution is intentionally left
  out. If you want to eventually wire that in, it needs its own separate,
  careful design with a manual confirmation step — not something to add
  casually once real money can move on a bug or bad signal.
- It does not run 24/7 unless you keep your laptop and ngrok tunnel open, or
  move it to real hosting later.
