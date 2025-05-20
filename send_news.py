import telegram
import feedparser
from datetime import datetime

# 你的 Telegram Bot Token 與 Chat ID（已填入）
TOKEN = '7915485999:AAHSYzBi1-Hh8PRvRRhbmnuafsey8BdNS8o'
CHAT_ID = '8079438887'

bot = telegram.Bot(token=TOKEN)

# 抓取 RSS 前五則新聞
def get_top_news_from_rss():
    feed_url = 'https://rss.udn.com/rss/money.xml'
    feed = feedparser.parse(feed_url)
    top_news = feed.entries[:5]

    news_list = []
    for i, entry in enumerate(top_news, start=1):
        title = entry.title
        link = entry.link
        news_list.append(f"<b>{i}. {title}</b>\n{link}")

    return news_list

# 傳送新聞訊息
def send_daily_news():
    today = datetime.now().strftime('%Y/%m/%d')
    header = f"<b>【{today} 經濟日報熱門新聞 Top 5】</b>"
    bot.send_message(chat_id=CHAT_ID, text=header, parse_mode="HTML")

    news_list = get_top_news_from_rss()
    for news in news_list:
        bot.send_message(chat_id=CHAT_ID, text=news, parse_mode="HTML")

# 主程式執行
if __name__ == '__main__':
    send_daily_news()
