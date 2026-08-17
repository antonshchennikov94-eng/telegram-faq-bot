"""
bot.py
Точка входа. Запускать по-прежнему командой: python bot.py

Логика разбита на модули:
  config.py     — токены, настройка ИИ-клиента
  database.py   — SQLite: постоянное хранение ответов и истории
  keyboards.py  — разметки клавиатур
  ai.py         — запрос к языковой модели
  handlers.py   — обработчики команд и сообщений
"""

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import TOKEN
import database
import handlers


def main() -> None:
    database.init_db()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", handlers.start))
    app.add_handler(CommandHandler("menu", handlers.menu))
    app.add_handler(CommandHandler("help", handlers.help_command))
    app.add_handler(CommandHandler("last", handlers.last_command))
    app.add_handler(CallbackQueryHandler(handlers.button_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.handle_message))
    app.add_handler(MessageHandler(~filters.TEXT & ~filters.COMMAND, handlers.handle_other))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()
