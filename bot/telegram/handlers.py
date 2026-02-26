# bot/telegram/handlers.py
# Все обработчики команд и callback-кнопок

import subprocess

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.config import ADMIN_IDS
from bot.core.controller import SystemController
from bot.monitor.server import ServerMonitor
from bot.storage.status_store import StatusStore
from bot.telegram.formatter import (
    format_ping,
    format_ports,
    format_services,
    format_status,
)
from bot.telegram.keyboards import clear_logs_keyboard, confirm_keyboard


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _is_admin(user_id: int) -> bool:
    """Если ADMIN_IDS пуст — команды доступны всем (режим разработки)."""
    if not ADMIN_IDS:
        return True
    return user_id in ADMIN_IDS


async def _deny(update: Update) -> None:
    await update.message.reply_text("❌ У вас нет прав для этой команды")


# ─────────────────────────────────────────────
# Команды
# ─────────────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "🖥 *БОТ МОНИТОРИНГА СЕРВЕРА*\n\n"
        "Добавь меня в канал — я отправлю статус и буду обновлять его каждые 5 минут\\.\n\n"
        "*КОМАНДЫ:*\n"
        "/status — текущий статус\n"
        "/services — список служб\n"
        "/ports — открытые порты\n"
        "/ping \\<хост\\> — пинг хоста\n"
        "/restart\\_service \\<имя\\> — перезапустить службу\n"
        "/logs \\<служба\\> \\[строк\\] — просмотр логов\n"
        "/reboot — перезагрузить сервер\n"
        "/clear\\_logs — очистить journalctl\n"
        "/close\\_port \\<порт\\> — закрыть порт\n"
        "/test\\_update — обновить статус в каналах прямо сейчас",
        parse_mode="MarkdownV2",
    )


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    monitor: ServerMonitor = context.bot_data["monitor"]
    await update.message.reply_text(format_status(monitor), parse_mode="Markdown")


async def cmd_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    monitor: ServerMonitor = context.bot_data["monitor"]
    services = monitor.get_running_services()
    await update.message.reply_text(format_services(services), parse_mode="Markdown")


async def cmd_ports(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    monitor: ServerMonitor = context.bot_data["monitor"]
    ports = monitor.get_open_ports()
    await update.message.reply_text(format_ports(ports), parse_mode="Markdown")


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await update.message.reply_text(
            "Использование: `/ping <хост>`\n"
            "Пример: `/ping google.com`",
            parse_mode="Markdown",
        )
        return
    host = context.args[0]
    await update.message.reply_text(f"🔄 Пингую `{host}`...", parse_mode="Markdown")
    monitor: ServerMonitor = context.bot_data["monitor"]
    result = monitor.ping_host(host)
    await update.message.reply_text(format_ping(result), parse_mode="Markdown")


async def cmd_restart_service(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id):
        await _deny(update)
        return
    if not context.args:
        await update.message.reply_text(
            "Использование: `/restart_service <имя_службы>`\n"
            "Пример: `/restart_service nginx`",
            parse_mode="Markdown",
        )
        return
    name = context.args[0]
    await update.message.reply_text(
        f"⚠️ Перезапустить службу `{name}`?",
        reply_markup=confirm_keyboard(f"restart_service:{name}"),
        parse_mode="Markdown",
    )


async def cmd_reboot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id):
        await _deny(update)
        return
    await update.message.reply_text(
        "⚠️ *ВНИМАНИЕ!* Перезагрузить сервер?",
        reply_markup=confirm_keyboard("reboot_server"),
        parse_mode="Markdown",
    )


async def cmd_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id):
        await _deny(update)
        return
    if not context.args:
        await update.message.reply_text(
            "Использование: `/logs <служба> [строк]`\n"
            "Пример: `/logs nginx 50`",
            parse_mode="Markdown",
        )
        return
    service = context.args[0]
    lines = int(context.args[1]) if len(context.args) > 1 and context.args[1].isdigit() else 50
    monitor: ServerMonitor = context.bot_data["monitor"]
    logs = monitor.get_logs(service, lines)
    if len(logs) > 4000:
        logs = logs[-4000:]
    await update.message.reply_text(
        f"📋 *Логи {service}:*\n```\n{logs}\n```",
        parse_mode="Markdown",
    )


async def cmd_clear_logs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id):
        await _deny(update)
        return
    await update.message.reply_text(
        "⚠️ Выберите что очистить:",
        reply_markup=clear_logs_keyboard(),
    )


async def cmd_close_port(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id):
        await _deny(update)
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text(
            "Использование: `/close_port <номер_порта>`\n"
            "Пример: `/close_port 8080`",
            parse_mode="Markdown",
        )
        return
    port = int(context.args[0])
    await update.message.reply_text(
        f"⚠️ Закрыть порт `{port}`? Это завершит процесс на нём.",
        reply_markup=confirm_keyboard(f"close_port:{port}"),
        parse_mode="Markdown",
    )


async def cmd_test_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update.effective_user.id):
        await _deny(update)
        return
    await update.message.reply_text("🔄 Обновляю статус во всех каналах...")
    await _update_status_messages(context)
    await update.message.reply_text("✅ Статус обновлён!")


# ─────────────────────────────────────────────
# Callback кнопки
# ─────────────────────────────────────────────

async def handle_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    controller: SystemController = context.bot_data["controller"]

    if data == "cancel":
        await query.edit_message_text("❌ Операция отменена")
        return

    if data.startswith("restart_service:"):
        name = data.split(":", 1)[1]
        await query.edit_message_text(f"🔄 Перезапускаю `{name}`...", parse_mode="Markdown")
        ok, msg = controller.service_action("restart", name)
        await query.edit_message_text(
            f"{'✅' if ok else '❌'} {msg}", parse_mode="Markdown"
        )

    elif data == "reboot_server":
        await query.edit_message_text("🔄 Перезагружаю сервер...")
        ok, msg = controller.reboot_server()
        await query.edit_message_text(f"{'✅' if ok else '❌'} {msg}")

    elif data == "clear_journalctl":
        await query.edit_message_text("🗑 Очищаю логи...")
        ok, msg = controller.clear_journal()
        await query.edit_message_text(
            f"{'✅' if ok else '❌'} {msg}", parse_mode="Markdown"
        )

    elif data.startswith("close_port:"):
        port = int(data.split(":", 1)[1])
        await query.edit_message_text(f"🔒 Закрываю порт {port}...")
        ok, msg = controller.close_port(port)
        await query.edit_message_text(f"{'✅' if ok else '❌'} {msg}")


# ─────────────────────────────────────────────
# Авто-добавление в канал
# ─────────────────────────────────────────────

async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    for member in update.message.new_chat_members:
        if member.id == context.bot.id:
            monitor: ServerMonitor = context.bot_data["monitor"]
            store: StatusStore = context.bot_data["store"]
            chat_id = update.effective_chat.id
            text = format_status(monitor)
            sent = await context.bot.send_message(
                chat_id=chat_id, text=text, parse_mode="Markdown"
            )
            store.add_channel(chat_id, sent.message_id)
            print(f"✅ Бот добавлен в канал {chat_id}, message_id: {sent.message_id}")


# ─────────────────────────────────────────────
# Периодическое обновление статуса
# ─────────────────────────────────────────────

async def _update_status_messages(context: ContextTypes.DEFAULT_TYPE) -> None:
    monitor: ServerMonitor = context.bot_data["monitor"]
    store: StatusStore = context.bot_data["store"]
    text = format_status(monitor)

    for chat_id, message_id in store.get_channels().items():
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode="Markdown",
            )
        except Exception as e:
            print(f"⚠️  Ошибка обновления сообщения в {chat_id}: {e}")


async def job_update_status(context: ContextTypes.DEFAULT_TYPE) -> None:
    await _update_status_messages(context)


# ─────────────────────────────────────────────
# Регистрация
# ─────────────────────────────────────────────

def register_handlers(application: Application) -> None:
    # Команды
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("services", cmd_services))
    application.add_handler(CommandHandler("ports", cmd_ports))
    application.add_handler(CommandHandler("ping", cmd_ping))
    application.add_handler(CommandHandler("restart_service", cmd_restart_service))
    application.add_handler(CommandHandler("reboot", cmd_reboot))
    application.add_handler(CommandHandler("logs", cmd_logs))
    application.add_handler(CommandHandler("clear_logs", cmd_clear_logs))
    application.add_handler(CommandHandler("close_port", cmd_close_port))
    application.add_handler(CommandHandler("test_update", cmd_test_update))

    # Callback кнопки
    application.add_handler(CallbackQueryHandler(handle_callbacks))

    # Добавление в канал
    application.add_handler(
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, handle_new_member)
    )
