import os
import openai
import feedparser
import logging
import asyncio
from flask import Flask, request
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

# 設定 OpenAI API 金鑰
openai.api_key = os.getenv("OPENAI_API_KEY")

# Telegram Bot Token
BOT_TOKEN = "7915485999:AAHSYzBi1-Hh8PRvRRhbmnuafsey8BdNS8o"
WEBHOOK_URL = "https://finnews1688-bot.onrender.com"  # Render 會自動給你

# 設定經濟日報 RSS 源
RSS_URL = "https://money.udn.com/rssfeed/news/6215/4097878"

# 設定摘要的最大字數
SUMMARY_MAX_TOKENS = 300

# 設定摘要的溫度
SUMMARY_TEMPERATURE = 0.7

# 設定摘要的提示語
SUMMARY_PROMPT = "請將以下新聞內容進行摘要，並控制在 300 字以內：\n\n"

# 初始化 Flask 應用
app = Flask(__name__)

# 設定 Telegram Bot 的應用程式
application = ApplicationBuilder().token(BOT_TOKEN).build()

# 設定日誌紀錄
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# 定義 /start 指令的處理函數
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("你好，我是 FinNews Bot！輸入 /news 查看今日重點新聞。")

# 定義 /news 指令的處理函數
async def news(update: Update, context: CallbackContext):
    # 解析 RSS 源
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        await update.message.reply_text("目前沒有最新的新聞。")
        return

    # 取得最新的新聞條目
    latest_entry = feed.entries[0]
    title = latest_entry.title
    link = latest_entry.link
    published = datetime(*latest_entry.published_parsed[:6])

    # 取得新聞內容
    summary = await get_news_summary(latest_entry.summary)

    # 發送新聞摘要給用戶
    await update.message.reply_text(f"📢 最新新聞：{title}\n\n"
                                    f"🕒 發佈時間：{published.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                                    f"🔗 來源連結：{link}\n\n"
                                    f"📝 摘要：\n{summary}")

# 定義取得新聞摘要的函數
async def get_news_summary(news_content: str) -> str:
    # 構建 OpenAI 的提示語
    prompt = SUMMARY_PROMPT + news_content

    # 呼叫 OpenAI API 生成摘要
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=prompt,
        max_tokens=SUMMARY_MAX_TOKENS,
        temperature=SUMMARY_TEMPERATURE
    )

    # 取得摘要結果
    summary = response.choices[0].text.strip()
    return summary

# 定義 Webhook 設定
async def setup_webhook():
    await application.bot.delete_webhook()
    await application.bot.set_webhook(url=WEBHOOK_URL)

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

# 設定定時發送新聞摘要的函數
async def send_daily_news():
    # 解析 RSS 源
    feed = feedparser.parse(RSS_URL)
    if not feed.entries:
        logger.warning("目前沒有最新的新聞。")
        return

    # 取得最新的新聞條目
    latest_entry = feed.entries[0]
    title = latest_entry.title
    link = latest_entry.link
    published = datetime(*latest_entry.published_parsed[:6])

    # 取得新聞內容
    summary = await get_news_summary(latest_entry.summary)

    # 發送新聞摘要給所有用戶
    users = await application.bot.get_chat_administrators(chat_id="@FinNewsBot")
    for user in users:
        try:
            await application.bot.send_message(
                chat_id=user.user.id,
                text=f"📢 最新新聞：{title}\n\n"
                     f"🕒 發佈時間：{published.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                     f"🔗 來源連結：{link}\n\n"
                     f"📝 摘要：\n{summary}"
            )
        except Exception as e:
            logger.error(f"無法發送訊息給用戶 {user.user.id}: {e}")

# 設定定時任務
scheduler = AsyncIOScheduler()
scheduler.add_job(
    send_daily_news,
    IntervalTrigger(hours=24, start_date="2025-05-05 09:00:00", timezone="Asia/Taipei"),
    id="daily_news",
    replace_existing=True
)

# 啟動定時任務
scheduler.start()

# 設定 /start 和 /news 指令的處理器
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("news", news))

# 啟動應用程式
if __name__ == "__main__":
    asyncio.run(setup_webhook())  # 設定 webhook
    app.run(host='0.0.0.0', port=10000)  # 運行 Flask 應用
