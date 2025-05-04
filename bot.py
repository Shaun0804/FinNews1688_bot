from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 設置 Bot Token
BOT_TOKEN = '7915485999:AAHSYzBi1-Hh8PRvRRhbmnuafsey8BdNS8o'

# 設置 Polling 配置
app = ApplicationBuilder().token(BOT_TOKEN).build()

# 加入命令處理函式
async def start(update, context):
    await update.message.reply_text("Bot is working!")

app.add_handler(CommandHandler("start", start))

# 設置 Polling 參數
app.run_polling(poll_interval=1, timeout=10, drop_pending_updates=True)