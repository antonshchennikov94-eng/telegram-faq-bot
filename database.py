"""
database.py
Работа с базой данных SQLite. Раньше состояние пользователя (последнее
сообщение) хранилось только в оперативной памяти (context.user_data) и
полностью пропадало при каждом перезапуске бота (например, на Railway
при обновлении кода или обычном рестарте). Теперь оно сохраняется на
диск и переживает перезапуск.

Заодно сюда же перенесены ответы по ключевым словам — раньше они жили
в отдельном answers.json. При первом запуске (если таблица answers
пустая) содержимое answers.json автоматически подгружается в базу —
ничего из твоих старых ответов не потеряется.
"""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

DB_PATH = os.path.join(os.path.dirname(__file__), "bot_data.db")
ANSWERS_JSON_PATH = os.path.join(os.path.dirname(__file__), "answers.json")


@contextmanager
def get_connection():
    """Одно подключение на операцию — просто и безопасно для небольшого бота."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    """
    Создаёт таблицы, если их ещё нет, и один раз переносит ответы
    из answers.json в базу (если таблица answers пока пустая).
    Вызывается один раз при старте бота.
    """
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS user_state (
                user_id INTEGER PRIMARY KEY,
                last_message TEXT,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS answers (
                keyword TEXT PRIMARY KEY,
                answer TEXT NOT NULL
            )
            """
        )

        count = conn.execute("SELECT COUNT(*) AS c FROM answers").fetchone()["c"]
        if count == 0 and os.path.exists(ANSWERS_JSON_PATH):
            with open(ANSWERS_JSON_PATH, "r", encoding="utf-8") as f:
                old_answers = json.load(f)
            conn.executemany(
                "INSERT INTO answers (keyword, answer) VALUES (?, ?)",
                list(old_answers.items()),
            )
            print(f"[database] Перенесено {len(old_answers)} ответов из answers.json в базу")


def get_all_answers() -> dict[str, str]:
    """Возвращает все пары ключевое_слово -> ответ."""
    with get_connection() as conn:
        rows = conn.execute("SELECT keyword, answer FROM answers").fetchall()
        return {row["keyword"]: row["answer"] for row in rows}


def save_last_message(user_id: int, text: str) -> None:
    """Сохраняет последнее сообщение пользователя — переживёт перезапуск бота."""
    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO user_state (user_id, last_message, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                last_message = excluded.last_message,
                updated_at = excluded.updated_at
            """,
            (user_id, text, datetime.now(timezone.utc).isoformat()),
        )


def get_last_message(user_id: int) -> str | None:
    """Возвращает последнее сохранённое сообщение пользователя, если оно есть."""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT last_message FROM user_state WHERE user_id = ?", (user_id,)
        ).fetchone()
        return row["last_message"] if row else None
