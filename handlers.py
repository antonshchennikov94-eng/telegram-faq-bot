"""
handlers.py
Все обработчики команд и сообщений бота.

Ответы по ключевым словам теперь читаются из базы данных (database.py)
при каждом вызове — для такого небольшого бота это не создаёт заметной
задержки, зато не нужно заботиться о порядке загрузки данных при старте.
"""

from telegram import Update
from telegram.ext import ContextTypes

import database
from ai import ask_ai
from keyboards import main_keyboard, inline_menu_keyboard


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я твой первый бот.", reply_markup=main_keyboard)


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите вопрос:", reply_markup=inline_menu_keyboard)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keys = ", ".join(database.get_all_answers().keys())
    text = (
        "Вот что я умею:\n\n"
        f"— Отвечаю на слова: {keys}\n"
        "— На остальные вопросы отвечает ИИ 🤖\n"
        "— /start — начать сначала\n"
        "— /menu — показать меню с кнопками\n"
        "— /last — показать ваш последний вопрос"
    )
    await update.message.reply_text(text)


async def last_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Раньше последнее сообщение хранилось только в context.user_data и
    пропадало при перезапуске бота. Теперь оно читается из базы —
    сохраняется даже после перезапуска на Railway.
    """
    user_id = update.effective_user.id
    last = database.get_last_message(user_id)
    if last:
        await update.message.reply_text(f"Ваше последнее сообщение было: «{last}»")
    else:
        await update.message.reply_text("Вы мне пока ничего не писали.")


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "how_are_you":
        await query.edit_message_text("Отлично, я же бот — у меня всегда всё стабильно 🙂")
    elif query.data == "help":
        keys = ", ".join(database.get_all_answers().keys())
        await query.edit_message_text(f"Я понимаю такие слова: {keys}")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    user_id = update.effective_user.id

    database.save_last_message(user_id, update.message.text)

    for keyword, answer in database.get_all_answers().items():
        if keyword in text:
            await update.message.reply_text(answer)
            return

    await update.message.chat.send_action("typing")
    ai_answer = ask_ai(update.message.text)
    await update.message.reply_text(ai_answer)


async def handle_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Пока я понимаю только текстовые сообщения 🙂\nНапишите словами, чем могу помочь."
    )
