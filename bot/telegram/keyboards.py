# keyboards.py
# InlineKeyboardMarkup

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def services_keyboard(services):
    keyboard = []
    for srv in services:
        icon = "🟢" if srv["active"] else "🔴"
        keyboard.append([InlineKeyboardButton(f"{icon} {srv['name']}", callback_data=f"service:{srv['name']}")])
    keyboard.append([InlineKeyboardButton("⬅ Back", callback_data="dashboard")])
    return InlineKeyboardMarkup(keyboard)
