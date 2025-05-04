from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 將這裡的 TOKEN 換成你從 BotFather 拿到的 Bot Token
BOT_TOKEN = '7915485999:AAHSYzBi1-Hh8PRvRRhbmnuafsey8BdNS8o'

# /start 指令處理函式
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "嗨！我是 FinNews Bot 📈\n\n我每天會幫你精選經濟日報的財經新聞，還會附上我的觀點！\n\n輸入 /help 看看有什麼功能吧！"
    )

# /help 指令處理函式
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - 開始使用\n"
        "/help - 查看指令\n"
        "/today - 查看今天的精選新聞（即將開放）"
    )

# 建立 bot 應用程式並啟動
app = ApplicationBuilder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("help", help_command))

print("🤖 FinNews Bot 正在運作中...")
app.run_polling()