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

1. Go to https://groww.in/trade-api/api-keys and generate `GROWW_API_KEY` /
   `GROWW_API_SECRET`
2. **Note:** these expire daily — you'll need to regenerate them each trading
   morning before the pipeline can use this feature that day
3. Add both to `.env` (or Render's Environment tab if deployed)
4. Leave them blank any day you don't want this — the pipeline works fine
   without it, it just skips the portfolio context silently

## 10. Optional: deploy to the cloud (no laptop needed)

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
