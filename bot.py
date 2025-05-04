import logging
import requests
from bs4 import BeautifulSoup
import openai
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import openai
import os
# === 設定區 ===
BOT_TOKEN = "7915485999:AAHSYzBi1-Hh8PRvRRhbmnuafsey8BdNS8o"
WEBHOOK_URL = "https://finnews1688-bot.onrender.com"  # Render 會自動給你


# 獲取 OpenAI API 密鑰
openai_api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = openai_api_key
# 使用這個密鑰來進行 OpenAI API 呼叫

# ===========

app = Flask(__name__)

# 建立 Telegram Application（代替 Dispatcher）
application = Application.builder().token(BOT_TOKEN).build()

# === 抓取新聞 ===
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

# === GPT 摘要 ===
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
        return f"❗️產生摘要時出錯：{e}"

# === /news 指令處理器 ===
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    articles = fetch_udn_news()
    for title, link in articles:
        summary = summarize(title, link)
        await update.message.reply_text(f"📰 {title}\n🔗 {link}\n\n{summary}")

application.add_handler(CommandHandler("news", news))

# === Webhook 路由 ===
@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    application.update_queue.put_nowait(Update.de_json(data, application.bot))
    return "ok"

# === 初次啟動時設定 Webhook ===
@app.before_first_request
def init_webhook():
    application.bot.delete_webhook()
    application.bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

# === 啟動 Flask App ===
if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)