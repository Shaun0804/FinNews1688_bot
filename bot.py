from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import openai
import os
import asyncio

# Flask 應用
app = Flask(__name__)

# 從環境變數中讀取 API Key 與 Bot Token
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = "7915485999:AAHSYzBi1-Hh8PRvRRhbmnuafsey8BdNS8o"
WEBHOOK_URL = "https://finnews1688-bot.onrender.com"  # Render 會自動給你  # Render 會自動給你

# 設定 OpenAI API 金鑰
openai.api_key = OPENAI_API_KEY

# Telegram Bot Application
application = ApplicationBuilder().token(BOT_TOKEN).build()

# 回應 /start 指令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("你好，我是 FinNews Bot！輸入 /news 查看今日重點新聞。")

# 加入 handler
application.add_handler(CommandHandler("start", start))

# Flask 頁面 route（可避免 404）
@app.route('/')
def index():
    return 'FinNews Bot is running.'

# Webhook endpoint（同步處理）
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    application.update_queue.put(update)  # 放入更新隊列
    return 'ok', 200

# 啟動應用時設定 Webhook
async def setup_webhook():
    await application.bot.delete_webhook()
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

# 設定 Webhook 並啟動應用程式
if __name__ == '__main__':
    # 設定 Webhook
    asyncio.run(setup_webhook())
    
    # 啟動 Flask 伺服器
    app.run(host='0.0.0.0', port=10000)
