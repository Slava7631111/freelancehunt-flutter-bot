# Freelancehunt Flutter → Telegram → Auto Bid

Бот:
1. Проверяет открытые проекты через официальный Freelancehunt API v2.
2. Ищет Flutter/Dart/мобильные проекты по ключевым словам.
3. Присылает новый проект в Telegram.
4. Если `AUTO_BID=true`, автоматически делает ставку/отклик через официальный API.
5. Хранит обработанные проекты в `state.json`, чтобы не слать дубли.

## 1. Установка на macOS

Открой Terminal в этой папке и выполни:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 2. Получить Freelancehunt API token

В своём аккаунте Freelancehunt открой страницу **Apps and API / Приложения и API** и создай API token.
Вставь его в `.env`:

```env
FREELANCEHUNT_TOKEN=...
```

Никому не отправляй этот токен.

## 3. Создать Telegram-бота

1. В Telegram открой **@BotFather**.
2. `/newbot`
3. Скопируй token и вставь в `.env` как `TELEGRAM_BOT_TOKEN`.
4. Напиши своему новому боту любое сообщение.
5. В браузере открой:
   `https://api.telegram.org/botТВОЙ_ТОКЕН/getUpdates`
6. Найди `chat.id` и вставь его в `TELEGRAM_CHAT_ID`.

## 4. Сначала безопасная проверка

Оставь:

```env
AUTO_BID=true
DRY_RUN=true
```

Запусти:

```bash
python bot.py
```

Бот будет находить проекты и показывать, какой отклик он бы отправил, но реально ничего на Freelancehunt не отправит.

Когда убедишься, что фильтр и текст хорошие:

```env
DRY_RUN=false
```

и перезапусти бот.

## Важно про цену

Для ставки Freelancehunt требует `days`, `budget`, `safe_type` и `comment`.
Бот использует бюджет проекта, если он есть. Если его нет — берёт `DEFAULT_BID_AMOUNT` / `DEFAULT_BID_CURRENCY`.

Подстрой эти значения под себя до включения реальных автоставок.
