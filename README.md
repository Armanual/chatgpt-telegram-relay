# ChatGPT → Vercel → Telegram relay

Минимальный тестовый relay для проверки сценария:

ChatGPT browser → HTML button → Vercel Go Function → Telegram Bot API.

## Environment Variables

В Vercel добавьте:

- `TELEGRAM_BOT_TOKEN` — токен бота от BotFather.
- `TELEGRAM_CHAT_ID` — ID личного чата с ботом.
- `RELAY_KEY` — длинная случайная строка доступа.

## Запуск

После деплоя откройте:

```text
https://YOUR-PROJECT.vercel.app/?key=YOUR_RELAY_KEY
```

Страница сохранит ключ только в `sessionStorage`, уберёт его из адресной строки и активирует кнопку.

## Локальная разработка

```bash
vercel dev
```

Создайте локальный `.env` по примеру `.env.example`.
