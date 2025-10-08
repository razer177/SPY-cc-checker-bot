import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN not set!")

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
            await update.message.reply_text(f"💳 CC: `{cc}`\nStatus: *{status}*",
                                            parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ API error while checking card.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error: {e}")

app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_cc))

print("🤖 Bot is running...")
app.run_polling()
