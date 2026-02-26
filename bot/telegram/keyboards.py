# bot/telegram/keyboards.py
# Все inline клавиатуры

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def confirm_keyboard(yes_data: str, cancel_data: str = "cancel") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Да", callback_data=yes_data),
        InlineKeyboardButton("❌ Отмена", callback_data=cancel_data),
    ]])


def clear_logs_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🗑 Очистить journalctl", callback_data="clear_journalctl"),
        InlineKeyboardButton("❌ Отмена", callback_data="cancel"),
    ]])
