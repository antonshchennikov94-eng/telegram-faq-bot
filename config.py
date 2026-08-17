"""
config.py
Загрузка переменных окружения и настройка клиента ИИ (Groq).
Вынесено отдельно, чтобы токены и ключи не были разбросаны по всему коду.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TOKEN:
    raise RuntimeError(
        "BOT_TOKEN не найден в переменных окружения. "
        "Проверь файл .env — там должна быть строка BOT_TOKEN=..."
    )

ai_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
)

AI_MODEL = "llama-3.3-70b-versatile"
