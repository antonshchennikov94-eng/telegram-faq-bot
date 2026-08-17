"""
ai.py
Обращение к языковой модели (через Groq API) для ответа на вопросы,
не найденные в словаре ключевых слов.
"""

from config import ai_client, AI_MODEL


def ask_ai(user_text: str) -> str:
    response = ai_client.chat.completions.create(
        model=AI_MODEL,
        messages=[
            {
                "role": "system",
                "content": "Ты дружелюбный помощник в Telegram-боте. Отвечай кратко, 1-3 предложения, на русском языке.",
            },
            {"role": "user", "content": user_text},
        ],
    )
    return response.choices[0].message.content
