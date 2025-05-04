import os
import openai
import feedparser
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

# 設定 OpenAI API 金鑰
openai.api_key = os.getenv("OPENAI_API_KEY")

# Telegram Bot Token 與 Webhook 網址
BOT_TOKEN = "7915485999:AAHSYzBi1-Hh8PRvRRhbmnuafsey8BdNS8o"
WEBHOOK_URL = "https://finnews1688-bot.onrender.com"  # Render 會自動給你

# RSS 設定
RSS_URL = "https://money.udn.com/rssfeed/news/6215/4097878"
SUMMARY_MAX_TOKENS = 300
SUMMARY_TEMPERATURE = 0.7
SUMMARY_PROMPT = "請將以下新聞內容進行摘要，並控制在 300 字以內：\n\n"

# 初始化 Flask
app = Flask(__name__)

# Telegram Bot 應用
application = ApplicationBuilder().token(BOT_TOKEN).build()

# 記錄 log
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# /start 指令
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("你好，我是 FinNews Bot！輸入 /news 查看今日重點新聞。")

# /news 指令
async def news(update: Update, context: CallbackContext):
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        await update.message.reply_text("目前沒有最新的新聞。")
        return

    latest_entry = feed.entries[0]
    title = latest_entry.title
    link = latest_entry.link
    published = datetime(*latest_entry.published_parsed[:6])
    summary = await get_news_summary(latest_entry.summary)

    await update.message.reply_text(
        f"📢 最新新聞：{title}\n\n"
        f"🕒 發佈時間：{published.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"🔗 來源連結：{link}\n\n"
        f"📝 摘要：\n{summary}"
    )

# 摘要工具
async def get_news_summary(news_content: str) -> str:
    prompt = SUMMARY_PROMPT + news_content
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=SUMMARY_MAX_TOKENS,
        temperature=SUMMARY_TEMPERATURE
    )
    return response.choices[0].text.strip()

# Webhook 設定
async def setup_webhook():
    await application.bot.delete_webhook()
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")  # 加上 token！

# Webhook 接收
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
async def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    await application.process_update(update)
    return "ok"

# 首頁 route（避免 404）
@app.route("/", methods=["GET"])
def index():
    return "FinNews Bot is running."

# 定時推播新聞（預設 24 小時一次）
async def send_daily_news():
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        logger.warning("目前沒有最新的新聞。")
        return

    latest_entry = feed.entries[0]
    title = latest_entry.title
    link = latest_entry.link
    published = datetime(*latest_entry.published_parsed[:6])
    summary = await get_news_summary(latest_entry.summary)

    try:
        # 發送給測試用 chat_id（建議換成實際用戶列表或你的 Telegram chat_id）
        test_chat_id = 123456789  # 改成你自己的 chat_id
        await application.bot.send_message(
            chat_id=test_chat_id,
            text=f"📢 最新新聞：{title}\n\n"
                 f"🕒 發佈時間：{published.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                 f"🔗 來源連結：{link}\n\n"
                 f"📝 摘要：\n{summary}"
        )
    except Exception as e:
        logger.error(f"無法發送訊息: {e}")

# 加入指令處理器
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("news", news))

# 定時任務排程器
scheduler = AsyncIOScheduler()
scheduler.add_job(
    send_daily_news,
    IntervalTrigger(hours=24, start_date="2025-05-05 09:00:00", timezone="Asia/Taipei"),
    id="daily_news",
    replace_existing=True
)
scheduler.start()

# 啟動 Flask
if __name__ == "__main__":
    import asyncio
    asyncio.run(setup_webhook())
    app.run(host="0.0.0.0", port=10000)
