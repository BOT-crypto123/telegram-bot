"""
Telegram Bot — main entry point.
Commands:
  /start   — welcome message
  /help    — list available commands
  /echo    — repeat back your text  (/echo Hello!)
  /chatid  — show current chat ID (useful for debugging)
Any plain text message is echoed back automatically.
"""

import logging
import os

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────

HELP_TEXT = """
*Available commands*

/start — Welcome message
/help  — Show this help
/echo \<text\> — Repeat your text back
/chatid — Show the current chat ID

You can also just send any text and I'll echo it back\.
""".strip()


# ── Handlers ──────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a greeting when /start is issued."""
    user = update.effective_user
    await update.message.reply_markdown_v2(
        rf"Hi {user.mention_markdown_v2()}\! 👋"
        "\n\nI'm your bot\. Type /help to see what I can do\."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help text."""
    await update.message.reply_markdown_v2(HELP_TEXT)


async def echo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/echo <text> — repeat the supplied text."""
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Usage: /echo <your text here>")
        return
    await update.message.reply_text(text)


async def chatid_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reply with the current chat ID."""
    await update.message.reply_text(f"Chat ID: {update.effective_chat.id}")


async def echo_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo any plain text message back to the sender."""
    await update.message.reply_text(update.message.text)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN environment variable is not set. "
            "Create a bot via @BotFather and add the token as a secret."
        )

    app = Application.builder().token(token).build()

    # Register command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("echo", echo_command))
    app.add_handler(CommandHandler("chatid", chatid_command))

    # Echo all non-command text messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_message))

    logger.info("Bot is starting — polling for updates …")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
