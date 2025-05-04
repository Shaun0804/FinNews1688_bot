import logging
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import openai

# ====== 設定 ======
BOT_TOKEN = '7915485999:AAHSYzBi1-Hh8PRvRRhbmnuafsey8BdNS8o'
openai.api_key = "YOUR_OPENAI_KEY"
# ===================

# === 基本設定 ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# === 抓取新聞 ===
def fetch_udn_news():
    url = "https://money.udn.com/rank/newest/1001"  # 財經新聞
    headers = {"User-Agent": "Mozilla/5.0"}
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.text, "html.parser")

    articles = []
    for item in soup.select("div.story__content")[:3]:  # 最新三則
        title = item.select_one("h3 a").text.strip()
        link = "https://money.udn.com" + item.select_one("h3 a")["href"]
        articles.append((title, link))
    return articles

# === GPT 摘要與分析 ===
def summarize_and_analyze(title, url):
    prompt = f"""請針對這則新聞進行摘要與觀點分析：
標題：{title}
連結：{url}

請條列回覆，包含：
1. 新聞重點
2. 觀點分析（例如對金融市場、產業、消費者可能的影響）
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"⚠️ 產生摘要時發生錯誤：{e}"

# === /news 指令處理 ===
async def news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📡 正在取得最新財經新聞...")
    news_list = fetch_udn_news()

    for title, url in news_list:
        summary = summarize_and_analyze(title, url)
        msg = f"📰 {title}\n🔗 {url}\n\n{summary}"
        await update.message.reply_text(msg)

# === 主程式 ===
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("news", news))
    
    print("✅ FinNews Bot 已啟動，等待指令 /news")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
