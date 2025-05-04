from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import openai
import os
import asyncio
import feedparser

# Flask 應用
app = Flask(__name__)

# 從環境變數中讀取 API Key 與 Bot Token
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
BOT_TOKEN = "7915485999:AAHSYzBi1-Hh8PRvRRhbmnuafsey8BdNS8o"
WEBHOOK_URL = "https://finnews1688-bot.onrender.com"  # Render 會自動給你

# 設定 OpenAI API 金鑰
openai.api_key = OPENAI_API_KEY

# Telegram Bot Application
application = ApplicationBuilder().token(BOT_TOKEN).build()

# 回應 /start 指令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("你好，我是 FinNews Bot！輸入 /news 查看今日重點新聞。")

# 這裡可以接入經濟日報的 RSS 資料來提供新聞摘要
def get_economic_news():
    # 假設這是經濟日報的 RSS 來源
    rss_url = "https://www.example.com/rss"  # 請替換為經濟日報提供的實際 RSS 地址
    feed = feedparser.parse(rss_url)
    
    news_summary = "今日經濟日報重點新聞：\n\n"
    
    # 只顯示前 5 條新聞
    for entry in feed.entries[:5]:
        news_summary += f"標題: {entry.title}\n鏈接: {entry.link}\n\n"
    
    return news_summary

# 回應 /news 指令
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    news_summary = get_economic_news()  # 從 RSS 中獲取新聞摘要
    await update.message.reply_text(news_summary)

# 加入 handler
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("news", news))

# Flask 頁面 route（可避免 404）
@app.route('/')
def index():
    return 'FinNews Bot is running.'

# Webhook endpoint
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
async def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return 'ok'

# 啟動應用時設定 Webhook
async def setup_webhook():
    await application.bot.delete_webhook()
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

if __name__ == '__main__':
    # 設定 Webhook
    asyncio.run(setup_webhook())
    # 啟動 Flask 應用
    app.run(host='0.0.0.0', port=10000)
