import os
import openai
import feedparser
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import asyncio

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

    try:
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
    except Exception as e:
        logger.error(f"呼叫 OpenAI API 失敗: {e}")
        return "無法生成摘要，請稍後再試。"

# 定義定時發送新聞摘要的函數
async def send_daily_news():
    # 取得所有的用戶
    users = await application.bot.get_chat_administrators(chat_id="@FinNewsBot")

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

# 設定 Webhook
async def setup_webhook():
    await application.bot.delete_webhook()
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

# 啟動應用程式
if __name__ == "__main__":
    # 設定 Webhook
    asyncio.run(setup_webhook())
    application.run_polling()
