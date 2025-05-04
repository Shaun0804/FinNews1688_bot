import os
import logging
import feedparser
from datetime import datetime
from flask import Flask, request
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import openai
import asyncio

# ========= 環境變數設定 (建議不要硬編碼) =========
BOT_TOKEN = os.getenv("BOT_TOKEN") or "你的_bot_token"
WEBHOOK_URL = os.getenv("WEBHOOK_URL") or "https://yourdomain.com"
TEST_CHAT_ID = os.getenv("TEST_CHAT_ID") or "123456789"

openai.api_key = os.getenv("OPENAI_API_KEY") or "你的_openai_api_key"
RSS_URL = "https://money.udn.com/rssfeed/news/6215/4097878"

# ========= 初始化 =========
app = Flask(__name__)
application = ApplicationBuilder().token(BOT_TOKEN).build()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========= 指令定義 =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="你好，我是 FinNews Bot！輸入 /news 查看今日重點新聞。"
    )

async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="目前沒有最新的新聞。"
        )
        return

    latest_entry = feed.entries[0]
    title = latest_entry.title
    link = latest_entry.link
    try:
        published = datetime(*latest_entry.published_parsed[:6])
    except Exception:
        published = datetime.now()
    summary = await get_news_summary(latest_entry.summary)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f"📢 最新新聞：{title}\n\n"
            f"🕒 發佈時間：{published.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"🔗 來源連結：{link}\n\n"
            f"📝 摘要：\n{summary}"
        )
    )

# ========= 摘要工具 =========
async def get_news_summary(content: str) -> str:
    try:
        prompt = (
            f"請將以下新聞內容進行摘要，並控制在 300 字以內：\n\n{content}"
        )
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=300,
            temperature=0.7
        )
        if response.choices:
            return response.choices[0].text.strip()
        else:
            return "無法生成摘要，請稍後再試。"
    except Exception as e:
        logger.error(f"OpenAI 摘要錯誤: {e}")
        return "無法生成摘要，請稍後再試。"

# ========= Webhook 接收處理 =========
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    try:
        update = Update.de_json(request.get_json(force=True), application.bot)
        asyncio.create_task(application.process_update(update))
    except Exception as e:
        logger.error(f"Webhook 發生錯誤: {e}")
    return 'ok'

@app.route("/", methods=["GET"])
def index():
    return "FinNews Bot is running."

# ========= 定時推播功能 =========
async def send_daily_news():
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        logger.warning("目前沒有最新的新聞。")
        return

    latest_entry = feed.entries[0]
    title = latest_entry.title
    link = latest_entry.link
    try:
        published = datetime(*latest_entry.published_parsed[:6])
    except Exception:
        published = datetime.now()
    summary = await get_news_summary(latest_entry.summary)

    try:
        chat_id = int(TEST_CHAT_ID)
    except ValueError:
        logger.error("請設定有效的 TEST_CHAT_ID 環境變數。")
        return

    try:
        await application.bot.send_message(
            chat_id=chat_id,
            text=(
                f"📢 最新新聞：{title}\n\n"
                f"🕒 發佈時間：{published.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"🔗 來源連結：{link}\n\n"
                f"📝 摘要：\n{summary}"
            )
        )
    except Exception as e:
        logger.error(f"推播失敗: {e}")

# ========= 啟動流程 =========
async def main():
    # 加入指令
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("news", news))

    # 設定 Webhook（必須 await）
    await application.bot.delete_webhook()
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

    # 啟動定時任務
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        lambda: asyncio.create_task(send_daily_news()),
        IntervalTrigger(
            hours=24,
            start_date="2025-05-05 09:00:00",
            timezone="Asia/Taipei"
        ),
        id="daily_news",
        replace_existing=True
    )
    scheduler.start()

if __name__ == "__main__":
    # 先執行異步初始化，再啟動 Flask
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())

    # 在 Render 上通常會使用環境變數 PORT
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
