# handlers.py
# Все обработчики команд и callback кнопок

from telegram.ext import CommandHandler, CallbackQueryHandler

from bot.telegram.keyboards import services_keyboard

def register_handlers(application):
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(callbacks))

# Примеры функций
async def start_command(update, context):
    await update.message.reply_text("Бот запущен!")

async def callbacks(update, context):
    query = update.callback_query
    await query.answer()
    data = query.data
    # обработка callback
