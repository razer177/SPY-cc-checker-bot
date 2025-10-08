import os
import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("❌ TELEGRAM_BOT_TOKEN not set. Add it to your environment or .env file.")

API_URL = "https://chkr-api.vercel.app/api/check?cc="

# Flask app for webhook
app = Flask(__name__)

# Telegram application
application = Application.builder().token(BOT_TOKEN).build()

# Command: /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "💳 Welcome to *CC Checker Bot!*
\n"
        "Send a credit card number to check its status.
\n"
        "*Commands:*
"
        "/start - Show this message",
        parse_mode="Markdown"
    )

# Message handler: check CC
async def check_cc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cc = update.message.text.strip()
    if not cc or len(cc) < 8:
        await update.message.reply_text("⚠️ Please send a valid card number (min 8 digits).")
        return

    try:
        r = requests.get(API_URL + cc, timeout=10)
        data = r.json()
        status = data.get("status", "").lower()
        if "active" in status:
            reply = f"✅ Card `{cc}` is *ACTIVE*"
        elif "dead" in status or "invalid" in status:
            reply = f"❌ Card `{cc}` is *DEAD*"
        else:
            reply = f"ℹ️ Unknown status: {data}"
    except Exception as e:
        reply = f"❌ Error: {e}"

    await update.message.reply_text(reply, parse_mode="Markdown")

# Add handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_cc))

# Flask route to receive Telegram updates
@app.route(f"/webhook/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put_nowait(update)
    return "ok", 200

# Health check route
@app.route("/", methods=["GET"])
def home():
    return "🤖 CC Checker Bot is running!"

# Utility to set webhook
@app.route("/setwebhook")
def set_webhook():
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        return "❌ Set WEBHOOK_URL environment variable first", 400

    response = requests.get(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook?url={webhook_url}/webhook/{BOT_TOKEN}"
    )
    return response.text

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))
