# Telegram Bot

A Python Telegram bot built with `python-telegram-bot` v21. Responds to commands and echoes plain text messages.

## Run & Operate

- **Start the bot**: Use the "Telegram Bot" workflow (runs `python3 bot/main.py`)
- **Required secret**: `TELEGRAM_BOT_TOKEN` — set via Replit Secrets

## Stack

- Python 3.13
- [python-telegram-bot](https://python-telegram-bot.org/) v21 (async, polling mode)

## Where things live

- `bot/main.py` — bot entry point, all handlers
- `bot/requirements.txt` — Python dependencies (managed by uv via Replit)

## Bot commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message |
| `/help` | List available commands |
| `/echo <text>` | Repeat text back |
| `/chatid` | Show the current chat's ID |
| _(any text)_ | Echoed back automatically |

## Adding new commands

1. Write an `async def my_handler(update, context)` function in `bot/main.py`
2. Register it: `app.add_handler(CommandHandler("mycommand", my_handler))`
3. Restart the "Telegram Bot" workflow

## User preferences

_Populate as you build — explicit user instructions worth remembering across sessions._

## Gotchas

- Bot uses long-polling — no webhook setup needed for development
- `MarkdownV2` special characters (`!`, `.`, `-`, etc.) must be escaped with `\` in reply text
