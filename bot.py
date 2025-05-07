import os
import logging
import feedparser
import asyncio
import threading
import httpx
import re
import time

from datetime import datetime
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

# ========= 讀取環境變數 =========
BOT_TOKEN        = os.getenv("BOT_TOKEN")
WEBHOOK_URL      = os.getenv("WEBHOOK_URL")
TEST_CHAT_ID     = int(os.getenv("TEST_CHAT_ID"))
RSS_URL          = os.getenv("RSS_URL")
MISTRAL_API_KEY  = os.getenv("MISTRAL_API_KEY")

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
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="目前沒有最新的新聞。"
        )
        return

    entry = feed.entries[0]
    title = entry.title
    link = entry.link
    try:
        published = datetime(*entry.published_parsed[:6])
    except Exception:
        published = datetime.now()

    summary, advisor = await generate_news_analysis(entry.summary)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=(f"📢 最新新聞：{title}\n\n"
              f"🕒 發佈時間：{published:%Y-%m-%d %H:%M:%S}\n\n"
              f"🔗 來源連結：{link}\n\n"
              f"📝 摘要：\n{summary}\n\n"
              f"💡 理專觀點：\n{advisor}")
    )

# ========= 使用 Mistral 原生 API 產生摘要 =========
async def generate_news_analysis(content: str) -> tuple[str, str]:
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "mistral-small",
        "messages": [
            {
                "role": "system",
                "content": (
                    "你是一位財經新聞摘要助手，請用以下格式回答：\n"
                    "【摘要】新聞重點，不超過 300 字。\n"
                    "【理財建議】以理專角度評論此新聞對客戶的啟示與建議。\n"
                    "請務必用這兩個段落清楚分開。"
                )
            },
            {
                "role": "user",
                "content": f"請將以下新聞內容摘要，並加入理財專員的看法建議：\n\n{content}"
            }
        ],
        "temperature": 0.7,
        "max_tokens": 600
    }

    # 重新嘗試的邏輯：最多重試3次
    for attempt in range(3):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                result = response.json()
                full_text = result["choices"][0]["message"]["content"].strip()
                summary, advisor = parse_summary_and_advice(full_text)
                return summary, advisor
        except Exception as e:
            logger.error(f"Mistral 分析錯誤: {e} (嘗試 {attempt+1}/3)")
            if attempt < 2:
                time.sleep(2)  # 等待2秒後重試
            else:
                return "無法生成摘要，請稍後再試。", "無法生成理財觀點，請稍後再試。"

# ========parse_summary_and_advice()==============
def parse_summary_and_advice(text: str) -> tuple[str, str]:
    summary_match = re.search(r"【摘要】(.*?)【理財建議】", text, re.DOTALL)
    advice_match = re.search(r"【理財建議】(.*)", text, re.DOTALL)

    summary = summary_match.group(1).strip() if summary_match else "無法提取摘要段落。"
    advice = advice_match.group(1).strip() if advice_match else "無法提取理財觀點段落。"
    return summary, advice

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

    summary, advisor = await generate_news_analysis(entry.summary)
    
    try:
        await application.bot.send_message(
            chat_id=TEST_CHAT_ID,
            text=(f"📢 最新新聞：{title}\n\n"
                  f"🕒 發佈時間：{published:%Y-%m-%d %H:%M:%S}\n\n"
                  f"🔗 來源連結：{link}\n\n"
                  f"📝 摘要：\n{summary}\n\n"
                  f"💡 理專觀點：\n{advisor}")
        )
    except Exception as e:
        logger.error(f"推播失敗: {e}")

# ========= Webhook Endpoint =========
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)

    future = asyncio.run_coroutine_threadsafe(
        application.process_update(update),
        bot_loop
    )
    try:
        future.result(timeout=10)
    except Exception as e:
        logger.error(f"Webhook 處理失敗: {e}")
    return "ok"

@app.route("/", methods=["GET"])
def index():
    return "FinNews Bot is running."

# ========= 啟動 & 事件迴圈 =========
async def init_app():
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("news", news))
    application.add_handler(CommandHandler("today", news))  # 新增 today 指令

    await application.initialize()
    await application.start()

    await application.bot.delete_webhook()
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

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

def start_bot_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    loop.run_forever()

if __name__ == "__main__":
    bot_loop = asyncio.new_event_loop()
    bot_loop.run_until_complete(init_app())
    threading.Thread(target=start_bot_loop, args=(bot_loop,), daemon=True).start()

    port = int(os.getenv("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
