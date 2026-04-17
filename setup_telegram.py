#!/usr/bin/env python3
"""
Telegram Setup Helper — GH AutoPost
====================================
Помогает найти:
  TELEGRAM_CHANNEL_ID  — ID канала или супергруппы
  TELEGRAM_TOPIC_ID    — ID темы (topic/thread) внутри супергруппы

Использование:
  python setup_telegram.py
  python setup_telegram.py --token 1234567890:ABC...
"""

import argparse
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Установите зависимость: pip install requests")
    sys.exit(1)

# ── цвета (работают в macOS/Linux терминале) ─────────────────────────────────

GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

def g(s): return f"{GREEN}{s}{RESET}"
def y(s): return f"{YELLOW}{s}{RESET}"
def c(s): return f"{CYAN}{s}{RESET}"
def b(s): return f"{BOLD}{s}{RESET}"

def hr():
    print("─" * 60)

# ── Telegram API helpers ──────────────────────────────────────────────────────

def api(token: str, method: str, **kwargs):
    url = f"https://api.telegram.org/bot{token}/{method}"
    try:
        r = requests.get(url, params=kwargs, timeout=15)
        r.raise_for_status()
        data = r.json()
        if not data.get("ok"):
            return None, data.get("description", "unknown error")
        return data.get("result"), None
    except requests.RequestException as e:
        return None, str(e)


def get_me(token: str):
    return api(token, "getMe")


def clear_updates(token: str):
    """Сбросить очередь обновлений, чтобы не получать старые."""
    result, _ = api(token, "getUpdates", offset=-1, timeout=1)
    return result


def poll_updates(token: str, offset: int, timeout: int = 30):
    return api(token, "getUpdates", offset=offset, timeout=timeout,
               allowed_updates="message,channel_post")

# ── Парсинг обновлений ────────────────────────────────────────────────────────

def extract_chat_info(updates: list) -> list[dict]:
    """Из списка обновлений извлечь уникальные чаты и темы."""
    seen: dict[str, dict] = {}   # key = "chat_id:thread_id"

    for upd in updates:
        msg = upd.get("message") or upd.get("channel_post")
        if not msg:
            continue

        chat = msg.get("chat", {})
        chat_id   = chat.get("id")
        chat_type = chat.get("type")           # group / supergroup / channel
        chat_title = chat.get("title", "—")
        thread_id  = msg.get("message_thread_id")  # None если нет темы

        if chat_id is None:
            continue

        key = f"{chat_id}:{thread_id}"
        if key not in seen:
            seen[key] = {
                "chat_id":    chat_id,
                "chat_title": chat_title,
                "chat_type":  chat_type,
                "thread_id":  thread_id,
            }

    return list(seen.values())

# ── Основной флоу ─────────────────────────────────────────────────────────────

def ask_token() -> str:
    print()
    print(b("Введите токен Telegram-бота") + f" (от @BotFather):")
    print(c("  → ") + "Если .env уже есть, токен можно взять оттуда.")
    token = input("  Токен: ").strip()
    if not token:
        print("Токен не введён.")
        sys.exit(1)
    return token


def load_token_from_env() -> str | None:
    env_file = Path(".env")
    if not env_file.exists():
        return None
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            val = line.split("=", 1)[1].strip()
            return val if val and not val.startswith("#") else None
    return None


def step_verify_token(token: str) -> dict:
    print()
    print("Проверяю токен…")
    bot, err = get_me(token)
    if err or not bot:
        print(f"  Ошибка: {err}")
        sys.exit(1)
    name = bot.get("first_name", "")
    username = bot.get("username", "")
    print(g(f"  Бот найден: {name} (@{username})"))
    return bot


def step_add_bot():
    hr()
    print(b("ШАГ 1 — Добавьте бота в канал/супергруппу"))
    print()
    print("  1. Откройте нужный канал или супергруппу в Telegram.")
    print("  2. Перейдите в Управление → Администраторы → Добавить администратора.")
    print("  3. Найдите вашего бота по имени и добавьте его.")
    print("     Достаточно права «Отправка сообщений».")
    print()
    input("  Нажмите Enter, когда бот добавлен… ")


def step_send_message():
    hr()
    print(b("ШАГ 2 — Отправьте тестовое сообщение"))
    print()
    print("  Напишите " + y("любое сообщение") + " в канал или супергруппу,")
    print("  где добавлен бот.")
    print()
    print("  Хотите узнать ID темы (TELEGRAM_TOPIC_ID)?")
    print("  → Напишите сообщение " + y("именно в ту тему") + ", которую используете для новостей.")
    print()
    print("  Можно отправить несколько сообщений в разные темы —")
    print("  скрипт покажет все найденные.")
    print()
    input("  Нажмите Enter, когда сообщение(ия) отправлены… ")


def step_collect(token: str) -> list[dict]:
    hr()
    print(b("Получаю обновления от Telegram…"))
    print()

    # Сбросить старую очередь
    clear_updates(token)

    print("  Жду новых сообщений (до 40 секунд)…")
    print("  " + y("Если ничего не пришло — отправьте сообщение в чат ещё раз."))
    print()

    offset = 0
    deadline = time.time() + 40
    chats: list[dict] = []

    while time.time() < deadline and not chats:
        updates, err = poll_updates(token, offset=offset, timeout=10)
        if err:
            print(f"  Ошибка: {err}")
            time.sleep(3)
            continue
        if updates:
            chats = extract_chat_info(updates)
            # обновить offset
            offset = updates[-1]["update_id"] + 1

    return chats


def step_show_results(chats: list[dict]):
    hr()
    if not chats:
        print(y("Не получено ни одного сообщения."))
        print("Убедитесь, что:")
        print("  • бот добавлен как администратор")
        print("  • вы написали сообщение ПОСЛЕ нажатия Enter на предыдущем шаге")
        print("  • бот не заблокирован")
        print()
        print("Запустите скрипт ещё раз.")
        return

    print(b(f"Найдено чатов/тем: {len(chats)}"))
    print()

    env_lines = []

    for i, info in enumerate(chats, 1):
        chat_id    = info["chat_id"]
        chat_title = info["chat_title"]
        chat_type  = info["chat_type"]
        thread_id  = info["thread_id"]

        type_label = {
            "supergroup": "Супергруппа",
            "group":      "Группа",
            "channel":    "Канал",
        }.get(chat_type, chat_type)

        print(f"  {b(str(i))}. {g(chat_title)}  [{type_label}]")
        print(f"     TELEGRAM_CHANNEL_ID = {c(str(chat_id))}")

        if thread_id:
            print(f"     TELEGRAM_TOPIC_ID   = {c(str(thread_id))}  ← тема, в которую написали")
            env_lines.append((chat_id, thread_id, chat_title))
        else:
            print(f"     TELEGRAM_TOPIC_ID   = {c('0')}  (сообщение не в теме, или General)")
            env_lines.append((chat_id, 0, chat_title))
        print()

    hr()
    print(b("Скопируйте нужные строки в ваш .env:"))
    print()

    for chat_id, thread_id, title in env_lines:
        print(f"  # {title}")
        print(f"  {g('TELEGRAM_CHANNEL_ID')}={c(str(chat_id))}")
        print(f"  {g('TELEGRAM_TOPIC_ID')}={c(str(thread_id))}")
        print()

    hr()
    print(b("Совет:"))
    print("  Если каналов несколько — выберите тот, куда нужно постить.")
    print("  TELEGRAM_TOPIC_ID=0 означает «без темы» (публикация в General).")
    print()


# ── Точка входа ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Помощник настройки Telegram для GH AutoPost"
    )
    parser.add_argument("--token", help="Telegram Bot Token (если не хотите вводить вручную)")
    args = parser.parse_args()

    print()
    print(b("╔══════════════════════════════════════╗"))
    print(b("║   GH AutoPost — Telegram Setup       ║"))
    print(b("╚══════════════════════════════════════╝"))

    # Получить токен
    token = args.token
    if not token:
        token = load_token_from_env()
        if token:
            print()
            print(f"Найден токен в .env: {c(token[:20] + '…')}")
            answer = input("Использовать его? [Y/n]: ").strip().lower()
            if answer in ("n", "no", "нет"):
                token = ask_token()
        else:
            token = ask_token()

    bot = step_verify_token(token)
    _ = bot  # используется для отображения, дальше не нужен

    step_add_bot()
    step_send_message()

    chats = step_collect(token)
    step_show_results(chats)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nОтменено.")
        sys.exit(0)
