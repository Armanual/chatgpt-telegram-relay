# Telegram Study Planner Bot

Python backend для Telegram-бота учебного планирования и уведомлений, готовый к деплою на Vercel.

## Что уже есть

- Telegram webhook backend на FastAPI.
- Relay endpoint, совместимый с текущим каналом уведомлений: `/api/relay`, `/api/telegram/relay`, `/api/notify`.
- Команды: `/start`, `/today`, `/week`, `/tasks`, `/add`, `/deadlines`.
- Inline-кнопки для задач: `Done`, `Snooze`, `Reschedule`.
- Автоматические напоминания через Vercel Cron: `/api/cron/reminders`.
- Утренний план и вечерний итог.
- Repository-абстракция: SQLite/local по умолчанию, Postgres как точка расширения.
- Конфиг через env vars.
- Безопасная проверка `TELEGRAM_WEBHOOK_SECRET`, `RELAY_SECRET`, `CRON_SECRET`.
- Health endpoint: `/api/health`.
- GitHub-ready структура, тесты и Vercel config.

## Структура

```text
api/index.py                         # Vercel entrypoint
src/study_planner_bot/app.py          # FastAPI routes
src/study_planner_bot/config.py       # env config
src/study_planner_bot/models.py       # dataclass models
src/study_planner_bot/repository/     # repository interface + SQLite + Postgres stub
src/study_planner_bot/services/       # planner, formatting, reminders
src/study_planner_bot/telegram/       # Telegram client and update handler
tests/                                # локальные тесты
vercel.json                           # rewrites + cron
```

## Локальный запуск

1. Создай виртуальное окружение и поставь зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Создай `.env` из примера:

```bash
cp .env.example .env
```

3. Для локальной разработки можно оставить фейковый `TELEGRAM_BOT_TOKEN`. В этом режиме отправка сообщений работает как dry-run и не трогает Telegram API.

4. Запусти сервер:

```bash
uvicorn study_planner_bot.app:create_app --factory --reload
```

Если пакет не находится, запусти с `PYTHONPATH=src`.

## Telegram webhook

После деплоя укажи Telegram webhook на:

```text
https://<your-vercel-domain>/api/telegram/webhook
```

При установке webhook передай secret token, совпадающий с `TELEGRAM_WEBHOOK_SECRET`. Реальный bot token не храни в коде, только в env vars Vercel.

## Relay endpoint

Отправка уведомления через существующий relay-канал:

```bash
curl -X POST https://<your-vercel-domain>/api/relay \
  -H "Authorization: Bearer $RELAY_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"chat_id":123456789,"text":"Тестовое уведомление"}'
```

Также поддерживаются:

- `X-Relay-Secret: ...`
- поле JSON `secret`
- поле `message` вместо `text`
- `TELEGRAM_DEFAULT_CHAT_ID`, если `chat_id` не передан

## Команды

```text
/start
/today
/week
/tasks
/deadlines
/add task Подготовить физику | due 01.09 18:00 | remind 31.08 10:00
/add schedule mon 09:00 90 Математика
```

Дни недели для расписания: `mon`, `tue`, `wed`, `thu`, `fri`, `sat`, `sun`, а также русские варианты `пн`, `вт`, `ср`, `чт`, `пт`, `сб`, `вс`.

## Vercel env vars

Минимум для production:

```text
APP_ENV=production
TELEGRAM_BOT_TOKEN=...
TELEGRAM_WEBHOOK_SECRET=...
RELAY_SECRET=...
CRON_SECRET=...
APP_TIMEZONE=Europe/Moscow
DATABASE_URL=sqlite:///./data/study_planner.db
```

Для серьёзного production лучше подключить Postgres и реализовать `PostgresRepository` в `src/study_planner_bot/repository/postgres.py`. Остальная логика уже зависит от интерфейса `Repository`.

## Cron

`vercel.json` запускает `/api/cron/reminders` каждые 15 минут. Endpoint требует:

```text
Authorization: Bearer <CRON_SECRET>
```

или:

```text
X-Cron-Secret: <CRON_SECRET>
```

## Тесты

```bash
PYTHONPATH=src python -m unittest discover -s tests
```

Тесты проверяют SQLite repository, парсер `/add`, создание reminder-записей и security helpers.


## Vercel domain note

Use the production domain shown in Vercel Deployments or Domains when setting Telegram webhook.
