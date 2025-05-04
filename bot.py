import logging
import requests
from bs4 import BeautifulSoup
import openai
import telegram
from telegram import Update
from telegram.ext import CommandHandler, Dispatcher
from flask import Flask, request

# === 設定區 ===
BOT_TOKEN = "7915485999:AAHSYzBi1-Hh8PRvRRhbmnuafsey8BdNS8o"
WEBHOOK_URL = "https://finnews1688-bot.onrender.com"  # Render 會自動給你
openai.api_key = "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"
# ===========

# 建立 Flask App
app = Flask(__name__)
bot = telegram.Bot(token=BOT_TOKEN)
dispatcher = Dispatcher(bot=bot, update_queue=None, workers=0)

# === 指令功能 ===
def fetch_udn_news():
    url = "https://money.udn.com/rank/newest/1001"
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    articles = []
    for item in soup.select("div.story__content")[:3]:
        title = item.select_one("h3 a").text.strip()
        link = "https://money.udn.com" + item.select_one("h3 a")["href"]
        articles.append((title, link))
    return articles

def summarize(title, url):
    prompt = f"""請針對這則新聞進行摘要與觀點分析：
標題：{title}
連結：{url}
請條列重點與觀點分析。
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"❗️發生錯誤：{e}"

def handle_news(update: Update, context):
    articles = fetch_udn_news()
    for title, link in articles:
        summary = summarize(title, link)
        update.message.reply_text(f"📰 {title}\n🔗 {link}\n\n{summary}")

# === 加入指令處理器 ===
dispatcher.add_handler(CommandHandler("news", handle_news))

# === Webhook 路由 ===
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    update = telegram.Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

# === 啟用 Webhook ===
@app.before_first_request
def setup():
    bot.delete_webhook()  # 確保乾淨狀態
    bot.set_webhook(f"{WEBHOOK_URL}/{BOT_TOKEN}")

# === 啟動 Flask App ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
