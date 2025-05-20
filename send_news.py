import requests
from bs4 import BeautifulSoup
import telegram
from datetime import datetime

# 直接填入 Telegram Bot Token 和 Chat ID
TOKEN = '7915485999:AAHSYzBi1-Hh8PRvRRhbmnuafsey8BdNS8o'
CHAT_ID = '8079438887'

bot = telegram.Bot(token=TOKEN)

# 擷取經濟日報熱門新聞前 5 則
def get_top_news():
    url = 'https://money.udn.com/rank/pv/1001/0/'
    headers = {'User-Agent': 'Mozilla/5.0'}
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

# 傳送訊息
def send_daily_news():
    today = datetime.now().strftime('%Y/%m/%d')
    header = f"<b>【{today} 經濟日報熱門新聞 Top 5】</b>\n\n"
    body = "\n\n".join(get_top_news())
    message = header + body
    bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="HTML")

# 主程式執行
if __name__ == '__main__':
    send_daily_news()
