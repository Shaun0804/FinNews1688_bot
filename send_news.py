import requests
from bs4 import BeautifulSoup
import telegram
from datetime import datetime

# === Telegram 設定 ===
TOKEN = '7915485999:AAHSYzBi1-Hh8PRvRRhbmnuafsey8BdNS8o'
CHAT_ID = '8079438887'

# 初始化 Telegram Bot
bot = telegram.Bot(token=TOKEN)

# 抓取經濟日報排行榜前 5 則新聞
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
            news_list.append(f"{i}. {title}\n{link}")

    return "\n\n".join(news_list)

# 傳送訊息
def send_daily_news():
    today = datetime.now().strftime('%Y/%m/%d')
    news_text = get_top_news()
    message = f"【{today} 經濟日報熱門新聞 Top 5】\n\n{news_text}"
    bot.send_message(chat_id=CHAT_ID, text=message)

# 主程式
if __name__ == '__main__':
    send_daily_news()
