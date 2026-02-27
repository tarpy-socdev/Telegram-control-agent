# 📂 СТРУКТУРА РЕПОЗИТОРИЯ НА GITHUB

Вот как должны быть расположены все файлы:

```
Telegram-control-agent/
├── README.md                    # Главная документация
├── .gitignore                   # Что не коммитить
├── requirements.txt             # Python зависимости
├── .env.example                 # Пример конфига
├── install.sh                   # Установка и управление
├── update_bot_final.py          # Скрипт обновления
├── cleanup_channels.py          # Очистка каналов
├── deploy.sh                    # Деплой на сервер
│
└── bot/
    ├── __init__.py
    ├── main.py                  # Точка входа
    ├── config.py                # Чтение .env
    │
    ├── core/
    │   ├── __init__.py
    │   └── controller.py        # SSH, сервисы, перезагрузка
    │
    ├── monitor/
    │   ├── __init__.py
    │   └── server.py            # Мониторинг
    │
    ├── storage/
    │   ├── __init__.py
    │   └── status_store.py      # Хранилище данных
    │
    └── telegram/
        ├── __init__.py
        ├── handlers.py          # Обработчики команд
        ├── keyboards.py         # Кнопки меню
        └── formatter.py         # Форматирование
```

## ✅ ЧТО КОММИТИТЬ НА GITHUB

```
✅ Нужно коммитить:
  - README.md
  - .gitignore
  - requirements.txt
  - .env.example (ПРИМЕР БЕЗ ТОКЕНА!)
  - install.sh
  - deploy.sh
  - update_bot_final.py
  - cleanup_channels.py
  - bot/ (все файлы Python)

❌ НЕ КОММИТИТЬ:
  - .env (содержит BOT_TOKEN!)
  - status_messages.json (состояние бота)
  - venv/ (virtual environment)
  - __pycache__/ (скомпилированный Python)
  - *.pyc (байт-код)
  - /tmp/ и другие временные файлы
```

## 📝 .gitignore

```bash
# Виртуальное окружение
venv/
env/
ENV/
.venv

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# IDE
.vscode/
.idea/
*.swp
*.swo

# Переменные окружения
.env
.env.local
.env.*.local

# Состояние бота
status_messages.json
*.log

# Загруженные файлы
/tmp/tg_uploads/

# macOS
.DS_Store
.AppleDouble

# Окончательные файлы
*.bak
*.tmp
~*
```

## 📦 requirements.txt

```
python-telegram-bot==20.7
psutil==5.9.6
python-dotenv==1.0.0
```

## 🚀 ШАГИ ДЕПЛОЯ НА GITHUB

### 1. Инициализируем Git репозиторий (если его ещё нет)

```bash
cd Telegram-control-agent
git init
git add .
git commit -m "initial: telegram control agent bot"
git branch -M main
git remote add origin https://github.com/tarpy-socdev/Telegram-control-agent.git
git push -u origin main
```

### 2. Каждый раз при обновлении

```bash
# Создаёшь новые версии файлов (обновляешь локально)
# ...

# Коммитишь и пушишь
git add bot/ update_bot_final.py cleanup_channels.py README.md
git commit -m "feature: улучшено форматирование и фиксен SSH"
git push origin main

# На сервере просто выполняешь
cd /opt/tg-control-agent
./deploy.sh full

# Или вручную
curl -sO https://raw.githubusercontent.com/tarpy-socdev/Telegram-control-agent/main/update_bot_final.py
python3 update_bot_final.py
./install.sh restart
```

## 🔐 БЕЗОПАСНОСТЬ

### НИКОГДА не коммитьте BOT_TOKEN!

❌ НЕПРАВИЛЬНО:
```bash
# .env
BOT_TOKEN=7851126415:AAH1yKpCvlAIspUMXybMcgOTjwVlH8oGNtw
git add .env
git push  # ОПАСНО!
```

✅ ПРАВИЛЬНО:
```bash
# .env (не коммитить!)
BOT_TOKEN=7851126415:AAH1yKpCvlAIspUMXybMcgOTjwVlH8oGNtw

# .env.example (коммитить)
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
ADMIN_IDS=YOUR_ADMIN_ID
UPDATE_INTERVAL=30
```

### Если ты случайно запушил токен:

```bash
# 1. Немедленно отозови токен у @BotFather
#    /revoke → выбери бота → получи новый токен

# 2. Удали старый токен из Git истории
git filter-branch --tree-filter 'grep -r "7851126415:AAH" . && rm .env || true'
git push -f origin main

# 3. Обнови .env на сервере с новым токеном
```

## 📋 ФАЙЛЫ В КАЖДОЙ ДИРЕКТОРИИ

### `bot/__init__.py`
```python
# Пусто или с версией
__version__ = "2.0.0"
```

### `bot/core/__init__.py`
### `bot/monitor/__init__.py`
### `bot/storage/__init__.py`
### `bot/telegram/__init__.py`
```python
# Все пусто
```

### `.env.example`
```bash
# Telegram Bot Token от @BotFather
BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# ID администраторов (через запятую)
ADMIN_IDS=5805064246,12345678

# Интервал обновления статуса (в секундах, минимум 30)
UPDATE_INTERVAL=30
```

## 🔄 РАБОЧИЙ ПРОЦЕСС

```bash
# 1. Чишишь локальный код
nano bot/telegram/handlers.py

# 2. Синтаксис проверяешь локально
python3 -m py_compile bot/telegram/handlers.py

# 3. Коммитишь
git add bot/telegram/handlers.py
git commit -m "fix: улучшено обновление статуса"

# 4. Пушишь на GitHub
git push origin main

# 5. На сервере деплоишь
./deploy.sh pull && ./deploy.sh restart

# 6. Проверяешь логи
./deploy.sh logs
```

## 📊 ВЕРСИОНИРОВАНИЕ

Используй семантическое версионирование в сообщениях коммитов:

```bash
# Новая функция
git commit -m "feature: добавлена команда /stats"

# Исправление бага
git commit -m "fix: исправлена ошибка с SSH отключением"

# Улучшение (рефакторинг)
git commit -m "refactor: оптимизирован код обновления статуса"

# Документация
git commit -m "docs: обновлён README"

# Версия
git tag v2.0.0
git push origin v2.0.0
```

---

**После этого всё готово к загрузке на GitHub и использованию! 🚀**
