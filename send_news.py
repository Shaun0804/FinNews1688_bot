import os
import feedparser
from datetime import datetime
import asyncio
from telegram import Bot

# 讀取 Telegram token 和 chat ID
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise ValueError("❌ TOKEN 或 CHAT_ID 為空，請確認 GitHub Secrets 是否正確設定。")

bot = Bot(token=TOKEN)

# 擷取經濟日報熱門新聞（從 RSS）
def get_top_news_from_rss():
    rss_url = 'https://cdn.feedcontrol.net/10159/18186-p5aGyCG285DQq.xml'
    feed = feedparser.parse(rss_url)

    news_list = []
    for i, entry in enumerate(feed.entries[:5], start=1):  # 取前五則
        title = entry.title
        link = entry.link
        news_list.append(f"<b>{i}. {title}</b>\n{link}")

    return news_list

# 發送訊息
async def send_daily_news():
    today = datetime.now().strftime('%Y/%m/%d')
    header = f"<b>【{today} 經濟日報熱門新聞 Top 5】</b>"

    await bot.send_message(chat_id=CHAT_ID, text=header, parse_mode="HTML")

    news_list = get_top_news_from_rss()
    for news in news_list:
        await bot.send_message(chat_id=CHAT_ID, text=news, parse_mode="HTML")
        await asyncio.sleep(1.5)  # 等一下，避免被限速

# 主程式執行
if __name__ == '__main__':
    asyncio.run(send_daily_news())
