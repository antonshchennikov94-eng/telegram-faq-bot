import json
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

ai_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
)

with open("answers.json", "r", encoding="utf-8") as f:
    answers = json.load(f)

keyboard = ReplyKeyboardMarkup(
    [["Привет", "Как дела"],
     ["Помощь"]],
    resize_keyboard=True
)

inline_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("Как дела", callback_data="how_are_you")],
    [InlineKeyboardButton("Что умеешь", callback_data="help")],
])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Я твой первый бот.", reply_markup=keyboard)

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Выберите вопрос:", reply_markup=inline_keyboard)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keys = ", ".join(answers.keys())
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
    last = context.user_data.get("last_message")
    if last:
        await update.message.reply_text(f"Ваше последнее сообщение было: «{last}»")
    else:
        await update.message.reply_text("Вы мне пока ничего не писали в этой сессии.")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "how_are_you":
        await query.edit_message_text("Отлично, я же бот — у меня всегда всё стабильно 🙂")
    elif query.data == "help":
        keys = ", ".join(answers.keys())
        await query.edit_message_text(f"Я понимаю такие слова: {keys}")

def ask_ai(user_text: str) -> str:
    response = ai_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "Ты дружелюбный помощник в Telegram-боте. Отвечай кратко, 1-3 предложения, на русском языке.",
            },
            {"role": "user", "content": user_text},
        ],
    )
    return response.choices[0].message.content

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()

    context.user_data["last_message"] = update.message.text

    for key, answer in answers.items():
        if key in text:
            await update.message.reply_text(answer)
            return

    await update.message.chat.send_action("typing")
    ai_answer = ask_ai(update.message.text)
    await update.message.reply_text(ai_answer)

async def handle_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Пока я понимаю только текстовые сообщения 🙂\nНапишите словами, чем могу помочь."
    )

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("menu", menu))
app.add_handler(CommandHandler("help", help_command))
app.add_handler(CommandHandler("last", last_command))
app.add_handler(CallbackQueryHandler(button_click))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(MessageHandler(~filters.TEXT & ~filters.COMMAND, handle_other))

app.run_polling()