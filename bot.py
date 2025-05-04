import os
import openai
import feedparser
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import asyncio

# 設定 OpenAI API 金鑰
openai.api_key = os.getenv("OPENAI_API_KEY")

# Telegram Bot Token 與 Webhook 網址
BOT_TOKEN = "7915485999:AAHSYzBi1-Hh8PRvRRhbmnuafsey8BdNS8o"
WEBHOOK_URL = "https://finnews1688-bot.onrender.com"

# RSS 設定
RSS_URL = "https://money.udn.com/rssfeed/news/6215/4097878"
SUMMARY_MAX_TOKENS = 300
SUMMARY_TEMPERATURE = 0.7
SUMMARY_PROMPT = "請將以下新聞內容進行摘要，並控制在 300 字以內：\n\n"

# 初始化 Flask
app = Flask(__name__)

# 建立 Telegram 應用
application = ApplicationBuilder().token(BOT_TOKEN).build()

# 設定 log
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# /start 指令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="你好，我是 FinNews Bot！輸入 /news 查看今日重點新聞。")

# /news 指令
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="目前沒有最新的新聞。")
        return

    latest_entry = feed.entries[0]
    title = latest_entry.title
    link = latest_entry.link
    published = datetime(*latest_entry.published_parsed[:6])
    summary = get_news_summary(latest_entry.summary)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"📢 最新新聞：{title}\n\n"
             f"🕒 發佈時間：{published.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
             f"🔗 來源連結：{link}\n\n"
             f"📝 摘要：\n{summary}"
    )

# 取得新聞摘要（OpenAI）
def get_news_summary(news_content: str) -> str:
    prompt = SUMMARY_PROMPT + news_content
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=SUMMARY_MAX_TOKENS,
        temperature=SUMMARY_TEMPERATURE
    )
    return response.choices[0].text.strip()

# 處理 Webhook（注意是 async）
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def telegram_webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "ok"

# 首頁（避免 404）
@app.route("/", methods=["GET"])
def index():
    return "FinNews Bot is running."

# 每日推播新聞（簡單例子）
async def send_daily_news():
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        logger.warning("目前沒有最新的新聞。")
        return

    latest_entry = feed.entries[0]
    title = latest_entry.title
    link = latest_entry.link
    published = datetime(*latest_entry.published_parsed[:6])
    summary = get_news_summary(latest_entry.summary)

    try:
        test_chat_id = 123456789  # ⚠️ 請換成你的 chat_id
        await application.bot.send_message(
            chat_id=test_chat_id,
            text=f"📢 最新新聞：{title}\n\n"
                 f"🕒 發佈時間：{published.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                 f"🔗 來源連結：{link}\n\n"
                 f"📝 摘要：\n{summary}"
        )
    except Exception as e:
        logger.error(f"無法發送訊息: {e}")

# 設定 webhook（async）
async def setup_webhook():
    await application.bot.delete_webhook()
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

# 註冊指令處理器
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("news", news))

# 啟用排程器
scheduler = AsyncIOScheduler()
scheduler.add_job(
    send_daily_news,
    IntervalTrigger(hours=24, start_date="2025-05-05 09:00:00", timezone="Asia/Taipei"),
    id="daily_news",
    replace_existing=True
)
scheduler.start()

# 啟動 Flask 應用 + 設定 webhook
if __name__ == "__main__":
    asyncio.run(setup_webhook())
    app.run(host="0.0.0.0", port=10000)
