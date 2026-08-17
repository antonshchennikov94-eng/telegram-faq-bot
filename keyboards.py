"""
keyboards.py
Разметки клавиатур бота — вынесены отдельно, чтобы не загромождать
основную логику обработчиков.
"""

from telegram import ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup

main_keyboard = ReplyKeyboardMarkup(
    [["Привет", "Как дела"],
     ["Помощь"]],
    resize_keyboard=True,
)

inline_menu_keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("Как дела", callback_data="how_are_you")],
    [InlineKeyboardButton("Что умеешь", callback_data="help")],
])
