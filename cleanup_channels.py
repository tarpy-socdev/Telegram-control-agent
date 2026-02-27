#!/usr/bin/env python3
"""cleanup_channels.py — очистка старых сообщений из привязанных каналов"""
import asyncio
import json
import sys
from datetime import datetime, timedelta
from telegram import Bot

async def cleanup_channels(bot_token, status_file="status_messages.json", days=None):
    """
    Удаляет старые сообщения из каналов
    
    Args:
        days: количество дней (удалит сообщения добавленные более N дней назад)
              если None — удалит все сообщения
    """
    try:
        with open(status_file) as f:
            data = json.load(f)
    except:
        print("❌ Не могу прочитать файл статуса")
        return
    
    channels = data.get("channels", {})
    if not channels:
        print("⚠️  Нет привязанных каналов")
        return
    
    bot = Bot(token=bot_token)
    cutoff = datetime.now() - timedelta(days=days) if days else None
    removed_count = 0
    
    print(f"\n🧹 Очистка {'за последние ' + str(days) + ' дней' if days else 'ВСЕ сообщения'}...")
    print(f"📊 Каналов: {len(channels)}\n")
    
    for chat_id_str, msg_data in channels.items():
        chat_id = int(chat_id_str)
        
        # Совместимость со старым форматом (просто число) и новым (объект)
        if isinstance(msg_data, dict):
            msg_id = msg_data.get("msg_id")
            added_str = msg_data.get("added")
            added = datetime.fromisoformat(added_str) if added_str else None
        else:
            msg_id = msg_data
            added = None
        
        # Проверяем нужно ли удалять
        if cutoff and added and added > cutoff:
            continue
        
        try:
            await bot.delete_message(chat_id=chat_id, message_id=msg_id)
            print(f"✅ Удалено сообщение из чата {chat_id}")
            removed_count += 1
        except Exception as e:
            if "message to delete not found" in str(e) or "CHAT_NOT_FOUND" in str(e):
                print(f"⚠️  Сообщение в чате {chat_id} не найдено (уже удалено?)")
            else:
                print(f"❌ Ошибка в чате {chat_id}: {e}")
    
    print(f"\n✨ Готово! Удалено: {removed_count} сообщений")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Использование: python3 cleanup_channels.py <BOT_TOKEN> [дни]\n")
        print("Примеры:")
        print("  python3 cleanup_channels.py 7851126415:AAH... 7    # Удалить за 7 дней")
        print("  python3 cleanup_channels.py 7851126415:AAH... all  # Удалить ВСЕ")
        sys.exit(1)
    
    token = sys.argv[1]
    days = None
    
    if len(sys.argv) > 2:
        arg = sys.argv[2]
        if arg != "all":
            try:
                days = int(arg)
            except:
                print(f"❌ Неверный аргумент: {arg}")
                sys.exit(1)
    
    asyncio.run(cleanup_channels(token, days=days))
