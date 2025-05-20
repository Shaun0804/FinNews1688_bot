import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import asyncio
from telegram import Bot

# 從 GitHub Secrets 讀取
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TOKEN or not CHAT_ID:
    raise ValueError("❌ TOKEN 或 CHAT_ID 為空，請確認 GitHub Secrets 是否正確設定。")

bot = Bot(token=TOKEN)

def get_top_news():
    url = 'https://money.udn.com/rank/pv/1001/0/'
    headers = {
        'User-Agent': 'Mozilla/5.0'
    }
    res = requests.get(url, headers=headers)
    res.encoding = 'utf-8'
    soup = BeautifulSoup(res.text, 'html.parser')

    news_items = soup.select('.tab-content li')[:5]
    news_list = []

    for i, item in enumerate(news_items, start=1):
        a = item.find('a')
        if a:
            title = a.text.strip()
            link = f"https://money.udn.com{a['href']}"
            news_list.append(f"<b>{i}. {title}</b>\n{link}")

    return news_list

async def send_daily_news():
    today = datetime.now().strftime('%Y/%m/%d')
    header = f"<b>【{today} 經濟日報熱門新聞 Top 5】</b>"

    print("📤 Sending header...")
    await bot.send_message(chat_id=CHAT_ID, text=header, parse_mode="HTML")

    news_list = get_top_news()
    for news in news_list:
        print(f"📤 Sending news: {news[:20]}...")
        await bot.send_message(chat_id=CHAT_ID, text=news, parse_mode="HTML")

if __name__ == '__main__':
    print("✅ 開始執行")
    asyncio.run(send_daily_news())
