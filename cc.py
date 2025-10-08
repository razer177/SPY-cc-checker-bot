import os
import requests
import datetime
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv
import threading
import asyncio

# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN not set!")

# Create Flask app
app = Flask(__name__)
start_time = datetime.datetime.now()

# Create Telegram bot application
telegram_app = ApplicationBuilder().token(BOT_TOKEN).build()

# === Telegram Handlers ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("""💳 Welcome to *CC Checker Bot!*
Send me a CC number to check its status.""", parse_mode="Markdown")

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
    uptime = datetime.datetime.now() - start_time
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime_str = f"{hours}h {minutes}m {seconds}s"
    
    return f"""
    <!DOCTYPE html>
    <html>
        <head>
            <title>CC Checker Bot Status</title>
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    text-align: center;
                    margin: 0;
                    padding: 50px 20px;
                    min-height: 100vh;
                }}
                .container {{
                    background: rgba(255, 255, 255, 0.1);
                    backdrop-filter: blur(10px);
                    border-radius: 20px;
                    padding: 40px;
                    max-width: 600px;
                    margin: 0 auto;
                    box-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
                }}
                h1 {{ color: #4CAF50; margin-bottom: 30px; }}
                .status-item {{
                    background: rgba(255, 255, 255, 0.1);
                    margin: 15px 0;
                    padding: 15px;
                    border-radius: 10px;
                    border-left: 4px solid #4CAF50;
                }}
                .status-label {{ font-weight: bold; color: #FFD700; }}
                .refresh-btn {{
                    background: #4CAF50;
                    color: white;
                    border: none;
                    padding: 10px 20px;
                    border-radius: 5px;
                    cursor: pointer;
                    margin-top: 20px;
                    font-size: 16px;
                }}
                .refresh-btn:hover {{ background: #45a049; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 CC Checker Bot Status</h1>
                
                <div class="status-item">
                    <span class="status-label">Bot Status:</span> ✅ Online & Running
                </div>
                
                <div class="status-item">
                    <span class="status-label">Bot Token:</span> {BOT_TOKEN[:8]}{'*' * 20}
                </div>
                
                <div class="status-item">
                    <span class="status-label">Mode:</span> {'🌐 Webhook' if WEBHOOK_URL else '🔄 Polling'}
                </div>
                
                {f'<div class="status-item"><span class="status-label">Webhook URL:</span> {WEBHOOK_URL}</div>' if WEBHOOK_URL else ''}
                
                <div class="status-item">
                    <span class="status-label">Uptime:</span> {uptime_str}
                </div>
                
                <div class="status-item">
                    <span class="status-label">Started:</span> {start_time.strftime('%Y-%m-%d %H:%M:%S')}
                </div>
                
                <div class="status-item">
                    <span class="status-label">Server Time:</span> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
                
                <button class="refresh-btn" onclick="window.location.reload()">🔄 Refresh Status</button>
            </div>
        </body>
    </html>
    """

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    try:
        json_data = request.get_json(force=True)
        update = Update.de_json(json_data, telegram_app.bot)
        
        # Create new event loop for this thread if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Process the update
        loop.create_task(telegram_app.process_update(update))
        
        return jsonify({"ok": True})
    except Exception as e:
        print(f"Webhook error: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/setwebhook", methods=["GET"])
def set_webhook():
    if not WEBHOOK_URL:
        return "❌ Set WEBHOOK_URL environment variable first", 400

    try:
        webhook_url = f"{WEBHOOK_URL}/{BOT_TOKEN}"
        success = telegram_app.bot.set_webhook(webhook_url)
        if success:
            return f"✅ Webhook set successfully: {webhook_url}"
        return "❌ Failed to set webhook", 500
    except Exception as e:
        return f"❌ Error setting webhook: {e}", 500

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "healthy",
        "uptime_seconds": int((datetime.datetime.now() - start_time).total_seconds()),
        "bot_token_set": bool(BOT_TOKEN),
        "webhook_mode": bool(WEBHOOK_URL),
        "timestamp": datetime.datetime.now().isoformat()
    })

def run_flask():
    """Run Flask server in a separate thread"""
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)

if __name__ == "__main__":
    if WEBHOOK_URL:
        print(f"🌐 Starting Flask server with webhook mode on port 8080")
        print(f"📡 Webhook URL: {WEBHOOK_URL}/{BOT_TOKEN}")
        app.run(host="0.0.0.0", port=8080)
    else:
        print("🤖 Starting bot in polling mode...")
        print("🌐 Flask status server starting on port 8080")
        
        # Run Flask in a separate thread
        flask_thread = threading.Thread(target=run_flask, daemon=True)
        flask_thread.start()
        
        # Run bot polling in main thread
        telegram_app.run_polling()
