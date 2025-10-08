import os
import requests
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN not set!")

if not WEBHOOK_URL:
    print("⚠️ WEBHOOK_URL not set. Using polling mode instead of webhook.")

# Create Flask app
app = Flask(__name__)

# Create Telegram app
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# === Telegram Handlers ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""💳 Welcome to *CC Checker Bot!*
Send me a CC number to check its status.""")

async def check_cc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cc = update.message.text.strip()
    url = f"https://chkr-api.vercel.app/api/check?cc={cc}"

    try:
        response = requests.get(url, timeout=10)
        if response.ok:
            data = response.json()
            status = data.get("status", "Unknown")
            await update.message.reply_text(
                f"💳 CC: `{cc}`\nStatus: *{status}*",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ API error while checking card.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

telegram_app.add_handler(CommandHandler("start", start))
telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_cc))

# === Flask Routes ===

@app.route("/")
def home():
    return "✅ CC Checker Bot is online and ready!"

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    telegram_app.update_queue.put_nowait(update)
    return jsonify({"ok": True})

@app.route("/setwebhook", methods=["GET"])
def set_webhook():
    if not WEBHOOK_URL:
        return "❌ Set WEBHOOK_URL environment variable first", 400

    s = telegram_app.bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")
    if s:
        return f"✅ Webhook set to {WEBHOOK_URL}/{BOT_TOKEN}"
    else:
        return "❌ Failed to set webhook", 500


if __name__ == "__main__":
    if WEBHOOK_URL:
        # Run Flask with webhook mode
        print(f"🌐 Running with webhook: {WEBHOOK_URL}/{BOT_TOKEN}")
        app.run(host="0.0.0.0", port=5000)
    else:
        # Run bot directly with polling mode
        print("🤖 Running with polling mode (no webhook URL set)...")
        telegram_app.run_polling()
