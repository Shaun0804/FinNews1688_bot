import os
import logging
import feedparser
import asyncio
import threading

from datetime import datetime
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
import openai

# ========= 環境變數設定 =========
BOT_TOKEN    = os.getenv("BOT_TOKEN")    or "你的_bot_token"
WEBHOOK_URL  = os.getenv("WEBHOOK_URL")  or "https://yourdomain.com"
TEST_CHAT_ID = int(os.getenv("TEST_CHAT_ID","123456789"))

openai.api_key = os.getenv("OPENAI_API_KEY") or "你的_openai_api_key"
RSS_URL = "https://money.udn.com/rssfeed/news/6215/4097878"

# ========= 日誌設定 =========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========= Flask & Telegram Bot 初始化 =========
app = Flask(__name__)
application = ApplicationBuilder().token(BOT_TOKEN).build()

# ========= 指令定義 =========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="你好，我是 FinNews Bot！輸入 /news 查看今日重點新聞。"
    )

async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="目前沒有最新的新聞。")
        return

    entry = feed.entries[0]
    title = entry.title
    link = entry.link
    try:
        published = datetime(*entry.published_parsed[:6])
    except Exception:
        published = datetime.now()
    summary = await get_news_summary(entry.summary)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(
            f"📢 最新新聞：{title}\n\n"
            f"🕒 發佈時間：{published:%Y-%m-%d %H:%M:%S}\n\n"
            f"🔗 來源連結：{link}\n\n"
            f"📝 摘要：\n{summary}"
        )
    )

# ========= 摘要工具 =========
async def get_news_summary(content: str) -> str:
    try:
        prompt = f"請將以下新聞內容進行摘要，並控制在 300 字以內：\n\n{content}"
        resp = openai.Completion.create(
            model="text-davinci-003",
            prompt=prompt,
            max_tokens=300,
            temperature=0.7
        )
        if resp.choices:
            return resp.choices[0].text.strip()
        else:
            return "無法生成摘要，請稍後再試。"
    except Exception as e:
        logger.error(f"OpenAI 摘要錯誤: {e}")
        return "無法生成摘要，請稍後再試。"

# ========= 定時推播功能 =========
async def send_daily_news():
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        logger.warning("目前沒有最新的新聞。")
        return

    entry = feed.entries[0]
    title = entry.title
    link = entry.link
    try:
        published = datetime(*entry.published_parsed[:6])
    except Exception:
        published = datetime.now()
    summary = await get_news_summary(entry.summary)

    try:
        await application.bot.send_message(
            chat_id=TEST_CHAT_ID,
            text=(
                f"📢 最新新聞：{title}\n\n"
                f"🕒 發佈時間：{published:%Y-%m-%d %H:%M:%S}\n\n"
                f"🔗 來源連結：{link}\n\n"
                f"📝 摘要：\n{summary}"
            )
        )
    except Exception as e:
        logger.error(f"推播失敗: {e}")

# ========= Webhook Endpoint =========
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    """接收 Telegram Webhook，並把更新推到背景的 asyncio 迴圈裡處理"""
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    # 將協程提交到 bot_loop
    future = asyncio.run_coroutine_threadsafe(
        application.process_update(update),
        bot_loop
    )
    try:
        # 等最長 10 秒看有無錯
        future.result(timeout=10)
    except Exception as e:
        logger.error(f"Webhook 處理失敗: {e}")
    return "ok"

@app.route("/", methods=["GET"])
def index():
    return "FinNews Bot is running."

# ========= 啟動 & 事件迴圈 =========
def start_bot_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

async def init_app():
    # 註冊命令
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("news", news))

    # 刪除舊 Webhook、設置新 Webhook
    await application.bot.delete_webhook()
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

    # 啟動定時任務
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        lambda: asyncio.create_task(send_daily_news()),
        trigger=IntervalTrigger(
            hours=24,
            start_date="2025-05-05 09:00:00",
            timezone="Asia/Taipei"
        ),
        id="daily_news",
        replace_existing=True
    )
    scheduler.start()

if __name__ == "__main__":
    # 在這裡建立並啟動背景的 asyncio 事件迴圈
    bot_loop = asyncio.new_event_loop()
    bot_loop.run_until_complete(init_app())

    thread = threading.Thread(target=start_bot_loop, args=(bot_loop,), daemon=True)
    thread.start()

    # 啟動 Flask
    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
