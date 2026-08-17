"""
Мониторинг новых проектов на Kwork через email-уведомления
и отправка подходящих проектов в Telegram-бота.

Как это работает:
1. Раз в N минут скрипт заходит в почту (Gmail) по IMAP
2. Ищет НЕПРОЧИТАННЫЕ письма от news@kwork.ru
3. Достаёт текст письма, ищет ключевые слова (бот, python, telegram и т.д.)
4. Если совпадение есть — отправляет тебе сообщение в Telegram
5. Письмо остаётся прочитанным в Gmail (Gmail сам это делает при чтении через IMAP),
   поэтому повторно оно не попадёт в следующую проверку

Перед запуском:
- Впиши свои данные в файл .env (см. .env.example рядом)
- Установи зависимости: pip install python-dotenv requests --break-system-packages
"""

import imaplib
import email
from email.header import decode_header
import time
import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

# ---------- Настройки из .env ----------
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Отправитель писем, которые нас интересуют
KWORK_SENDER = "news@kwork.ru"

# Ключевые слова — если хотя бы одно встречается в письме, шлём уведомление
# (можно редактировать под себя)
KEYWORDS = [
    "бот", "bot", "telegram", "телеграм", "python", "питон",
    "скрипт", "chatgpt", "ии-бот", "ии бот", "chat-bot", "chat bot",
]

# Как часто проверять почту (в секундах). 900 = 15 минут
CHECK_INTERVAL_SECONDS = 900

# Сколько последних непрочитанных писем проверять за раз
MAX_EMAILS_PER_CHECK = 20


def decode_mime_words(s):
    """Декодирует тему письма, если она в непонятной кодировке"""
    decoded = decode_header(s)
    result = ""
    for text, charset in decoded:
        if isinstance(text, bytes):
            result += text.decode(charset or "utf-8", errors="ignore")
        else:
            result += text
    return result


def clean_html(html):
    """Убирает CSS/JS блоки целиком, затем все html-теги, оставляя чистый текст"""
    # Убираем содержимое <style>...</style> и <script>...</script> целиком
    html = re.sub(r"<style[^>]*>.*?</style>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    # Переносы строк на месте </p>, </div>, <br> — чтобы текст не слипался
    html = re.sub(r"</p>|</div>|<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    # Убираем оставшиеся теги
    text = re.sub(r"<[^>]+>", " ", html)
    # Декодируем частые html-сущности
    text = (text.replace("&nbsp;", " ")
                .replace("&amp;", "&")
                .replace("&quot;", '"')
                .replace("&#39;", "'"))
    return text


def get_email_body(msg):
    """Достаёт текстовое содержимое письма (учитывает html и plain)"""
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    body = part.get_payload(decode=True).decode(errors="ignore")
                except Exception:
                    pass
                break
            elif content_type == "text/html" and "attachment" not in content_disposition and not body:
                try:
                    html = part.get_payload(decode=True).decode(errors="ignore")
                    body = clean_html(html)
                except Exception:
                    pass
    else:
        try:
            body = msg.get_payload(decode=True).decode(errors="ignore")
        except Exception:
            pass
    # схлопываем лишние пробелы (но сохраняем переносы строк)
    body = re.sub(r"[ \t]+", " ", body)
    body = re.sub(r"\n\s*\n+", "\n\n", body)
    return body.strip()


def contains_keyword(text):
    text_lower = text.lower()
    return any(keyword.lower() in text_lower for keyword in KEYWORDS)


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        response = requests.post(url, data=payload, timeout=10)
        if response.status_code != 200:
            print(f"[Telegram] Ошибка отправки: {response.text}")
    except Exception as e:
        print(f"[Telegram] Не удалось отправить сообщение: {e}")


def check_mailbox():
    print("Подключаюсь к почте...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com", 993)
        mail.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        mail.select("inbox")

        # Ищем непрочитанные письма от Kwork
        status, messages = mail.search(None, f'(UNSEEN FROM "{KWORK_SENDER}")')
        if status != "OK":
            print("Не удалось выполнить поиск писем")
            return

        email_ids = messages[0].split()
        if not email_ids:
            print("Новых писем от Kwork нет")
            mail.logout()
            return

        print(f"Найдено новых писем: {len(email_ids)}")

        # Проверяем только последние N писем за раз
        for eid in email_ids[-MAX_EMAILS_PER_CHECK:]:
            status, msg_data = mail.fetch(eid, "(RFC822)")
            if status != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            subject = decode_mime_words(msg.get("Subject", ""))
            body = get_email_body(msg)

            full_text = f"{subject} {body}"

            if contains_keyword(full_text):
                # Обрезаем текст письма, чтобы сообщение в Telegram не было гигантским
                short_body = body[:600] + ("..." if len(body) > 600 else "")
                notification = (
                    f"🔔 <b>Новый проект на Kwork</b>\n\n"
                    f"<b>Тема:</b> {subject}\n\n"
                    f"{short_body}"
                )
                send_telegram_message(notification)
                print(f"Отправлено уведомление: {subject}")
            else:
                print(f"Пропущено (нет ключевых слов): {subject}")

        mail.logout()

    except imaplib.IMAP4.error as e:
        print(f"Ошибка авторизации IMAP: {e}")
    except Exception as e:
        print(f"Общая ошибка: {e}")


def main():
    if not all([GMAIL_USER, GMAIL_APP_PASSWORD, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID]):
        print("Ошибка: заполни все переменные в файле .env перед запуском")
        return

    print("Мониторинг Kwork запущен. Проверка каждые "
          f"{CHECK_INTERVAL_SECONDS // 60} минут. Останов — Ctrl+C.")

    while True:
        check_mailbox()
        time.sleep(CHECK_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
