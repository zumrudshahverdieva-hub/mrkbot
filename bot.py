import json
import logging
from pathlib import Path

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# =========================
# НАСТРОЙКИ
# =========================

import os

BOT_TOKEN = (os.getenv("8756837734:AAG3wO9zcsFNvpYbpbnaKRleAzpLDVNddpk") or "").strip()
ADMIN_ID = int((os.getenv("ADMIN_ID") or "1319442767").strip())



print("DEBUG ENV KEYS:", sorted([k for k in os.environ.keys() if "TOKEN" in k or "ADMIN" in k or "RAILWAY" in k]))
print("DEBUG BOT_TOKEN exists:", "BOT_TOKEN" in os.environ)
print("DEBUG BOT_TOKEN repr:", repr(os.environ.get("BOT_TOKEN")))
print("DEBUG ADMIN_ID raw:", repr(os.environ.get("ADMIN_ID")))

DB_FILE = Path("message_links.json")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


# =========================
# ХРАНЕНИЕ СВЯЗОК
# =========================
def load_links() -> dict:
    if DB_FILE.exists():
        try:
            return json.loads(DB_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_links(data: dict) -> None:
    DB_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


message_links = load_links()


# =========================
# /start
# =========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        "Здравствуйте! 👋\n\n"
        "Это бот для вопросов о поступлении в МРК.\n"
        "Вы можете написать сюда любой вопрос, и администратор ответит вам через бота.\n\n"
        "Например:\n"
        "• какие специальности есть в МРК\n"
        "• какие нужны документы\n"
        "• когда проходит день открытых дверей\n"
        "• какой проходной балл\n\n"
        "Просто отправьте сообщение."
    )
    if update.message:
        await update.message.reply_text(text)


# =========================
# /help
# =========================
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user

    if user and user.id == ADMIN_ID:
        text = (
            "Команды администратора:\n\n"
            "/start — приветственное сообщение\n"
            "/help — помощь\n"
            "/myid — показать ваш Telegram ID\n\n"
            "Как отвечать пользователю:\n"
            "1. Найдите сообщение с вопросом\n"
            "2. Нажмите 'Ответить'\n"
            "3. Напишите текст ответа\n"
            "4. Бот сам отправит его пользователю"
        )
    else:
        text = (
            "Напишите сюда любой вопрос о поступлении в МРК, "
            "и администратор ответит вам через бота."
        )

    if update.message:
        await update.message.reply_text(text)


# =========================
# /myid
# =========================
async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_id = update.effective_chat.id if update.effective_chat else "неизвестно"

    if update.message and user:
        await update.message.reply_text(
            f"Ваш user.id = {user.id}\n"
            f"Ваш chat_id = {chat_id}\n"
            f"Ваш username = @{user.username if user.username else 'нет'}"
        )


# =========================
# ОБРАБОТКА СООБЩЕНИЙ ОТ ПОЛЬЗОВАТЕЛЯ
# =========================
async def handle_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    user = update.effective_user
    chat_id = update.effective_chat.id if update.effective_chat else None

    if not message or not user or chat_id is None:
        print("Нет message, user или chat_id")
        return

    print(f"Пришло сообщение от user.id={user.id}, chat_id={chat_id}, text={message.text}")

    if user.id == ADMIN_ID:
        print("Это сообщение от администратора")
        await handle_admin_message(update, context)
        return

    user_name = user.full_name or "Пользователь"

    forwarded_text = (
        "📩 Новый вопрос по поступлению в МРК\n\n"
        f"Отправитель: {user_name}\n"
        f"ID диалога: {chat_id}\n\n"
        f"Сообщение:\n{message.text}"
    )

    try:
        sent_to_admin = await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=forwarded_text
        )
        print(f"Сообщение админу отправлено. message_id={sent_to_admin.message_id}")
    except Exception as e:
        print(f"Ошибка при отправке админу: {e}")
        await message.reply_text("Произошла ошибка при отправке вопроса администрации.")
        return

    message_links[str(sent_to_admin.message_id)] = chat_id
    save_links(message_links)

    await message.reply_text(
        "Ваш вопрос отправлен администрации МРК ✅\n"
        "Когда вам ответят, сообщение придёт сюда."
    )


# =========================
# ОБРАБОТКА ОТВЕТА АДМИНА
# =========================
async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message

    if not message:
        print("У админа нет message")
        return

    print(f"Сообщение от админа: {message.text}")

    if not message.reply_to_message:
        print("Админ написал не reply")
        await message.reply_text(
            "Чтобы ответить пользователю, нужно нажать 'Ответить' на сообщение, которое бот прислал с вопросом."
        )
        return

    replied_message_id = str(message.reply_to_message.message_id)
    print(f"Админ отвечает на message_id={replied_message_id}")

    user_chat_id = message_links.get(replied_message_id)

    if not user_chat_id:
        print("Не найден user_chat_id по replied_message_id")
        await message.reply_text("Не удалось определить, кому отправить ответ.")
        return

    try:
        await context.bot.send_message(
            chat_id=user_chat_id,
            text=f"📬 Ответ на ваш вопрос о поступлении в МРК:\n\n{message.text}"
        )
        print(f"Ответ отправлен пользователю chat_id={user_chat_id}")
    except Exception as e:
        print(f"Ошибка отправки пользователю: {e}")
        await message.reply_text("Не удалось отправить ответ пользователю.")
        return

    await message.reply_text("Ответ пользователю отправлен ✅")


# =========================
# ЗАПУСК
# =========================
def main() -> None:
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_user_message))

    print("Бот запущен...")
    app.run_polling()


if __name__ == "__main__":
    main()