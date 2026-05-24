"""
МОНИТОРИНГ ВАКАНСИЙ В РЕАЛЬНОМ ВРЕМЕНИ
=========================================
- Загружает чаты через ссылку на папку
- Следит за новыми сообщениями в реальном времени
- Фильтрует: только те кто ИЩЕТ специалиста
- Каждый час обновляет список чатов из папки
- Найденные вакансии отправляет в твой канал
"""

from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.chatlists import CheckChatlistInviteRequest
from telethon.errors import FloodWaitError
from datetime import datetime
import asyncio
import os

# ============================================================
# ДАННЫЕ ИЗ ПЕРЕМЕННЫХ ОКРУЖЕНИЯ RAILWAY
# ============================================================

API_ID = int(os.environ["API_ID"])
API_HASH = os.environ["API_HASH"]
SESSION = os.environ["SESSION"]
OUTPUT_CHANNEL = os.environ.get("OUTPUT_CHANNEL", "@kjbrcrc")
FOLDER_INVITE = os.environ.get("FOLDER_INVITE", "yefFo_EuHDQ4MDcy")

# ============================================================
# КЛЮЧЕВЫЕ СЛОВА (кого ищут)
# ============================================================

KEYWORDS = [
    "таргетолог",
    "таргетолога",
    "авитолог",
]

# ============================================================
# СТОП-СЛОВА (предложения услуг — пропускаем)
# ============================================================

STOP_WORDS = [
    "предлагаю услуги",
    "настрою",
    "#помогу",
    "яндекс",
    "запускаю",
    " vk ",
    "вконтакте",
    "предлагаю свои услуги",
    "оказываю услуги",
    "предоставляю услуги",
    "готов взяться",
    "готова взяться",
    "готов помочь",
    "готова помочь",
    "возьмусь за",
    "берусь за проект",
    "ищу заказы",
    "ищу клиентов",
    "ищу проект",
    "ищу проекты",
    "в поиске заказов",
    "в поиске клиентов",
    "в поиске проекта",
    "открыт к заказам",
    "открыта к заказам",
    "открыт к сотрудничеству",
    "открыта к сотрудничеству",
    "рассматриваю проекты",
    "рассматриваю заказы",
    "мое портфолио",
    "моё портфолио",
    "мои кейсы",
    "мои услуги",
    "портфолио:",
    "резюме",
    "мои работы",
    "примеры работ",
    "я таргетолог",
    "я авитолог",
    "я smm",
    "я специалист",
    "я маркетолог",
    "я занимаюсь",
    "я помогу",
    "я помогаю",
    "я настраиваю",
    "меня зовут",
    "обо мне:",
    "привет, я",
    "здравствуйте, я",
    "подписывайтесь",
    "мой канал",
    "пишите в лс",
    "пишите в личку",
    "стоимость услуг",
    "прайс",
    "мои цены",
    "стоимость работ",
]

FOLDER_REFRESH_INTERVAL = 3600  # 1 час

# ============================================================
# КОД
# ============================================================

client = TelegramClient(StringSession(SESSION), API_ID, API_HASH)

current_chat_ids: set = set()

def contains_keyword(text: str) -> str | None:
    text_lower = text.lower()
    for kw in KEYWORDS:
        if kw.lower() in text_lower:
            return kw
    return None

def contains_stop_word(text: str) -> str | None:
    text_lower = text.lower()
    for sw in STOP_WORDS:
        if sw.lower() in text_lower:
            return sw
    return None

def check_message(text: str) -> tuple[bool, str]:
    keyword = contains_keyword(text)
    if not keyword:
        return False, "нет ключевых слов"
    stop_word = contains_stop_word(text)
    if stop_word:
        return False, f"стоп-слово: '{stop_word}'"
    return True, keyword

async def send_vacancy(keyword: str, chat_name: str, link: str, text: str, when: datetime):
    preview = text[:500] + ("..." if len(text) > 500 else "")
    time_str = when.strftime("%d.%m.%Y %H:%M")

    message = (
        f"🔔 <b>ВАКАНСИЯ</b>\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"📌 Слово: <code>#{keyword}</code>\n"
        f"💬 Чат: {chat_name}\n"
        f"🕐 Время: {time_str}\n"
        f"🔗 <a href='{link}'>Открыть сообщение</a>\n\n"
        f"{preview}"
    )

    while True:
        try:
            await client.send_message(OUTPUT_CHANNEL, message, parse_mode="html", link_preview=False)
            print(f"[✓] Отправлено: '{keyword}' из {chat_name} ({time_str})")
            return
        except FloodWaitError as e:
            print(f"[⏳] Флуд-лимит — жду {e.seconds} сек...")
            await asyncio.sleep(e.seconds + 2)
        except Exception as e:
            print(f"[✗] Ошибка отправки: {e}")
            return

async def load_chats_from_folder() -> tuple[list, list]:
    try:
        result = await client(CheckChatlistInviteRequest(slug=FOLDER_INVITE))
    except Exception as e:
        print(f"[✗] Не удалось загрузить папку: {e}")
        return [], []

    all_peers = (getattr(result, "already_peers", []) or []) + (getattr(result, "peers", []) or [])

    entities = []
    chat_ids = []
    for peer in all_peers:
        try:
            entity = await client.get_entity(peer)
            entities.append(entity)
            chat_ids.append(entity.id)
        except Exception:
            pass

    return entities, chat_ids

def make_handler():
    async def handler(event):
        text = event.message.text or ""
        if not text:
            return

        should_send, reason = check_message(text)
        if not should_send:
            return

        chat = await event.get_chat()
        chat_name = getattr(chat, "title", None) or getattr(chat, "username", "неизвестный")

        username = getattr(chat, "username", None)
        link = (
            f"https://t.me/{username}/{event.message.id}"
            if username
            else f"https://t.me/c/{str(event.chat_id).replace('-100', '')}/{event.message.id}"
        )

        await send_vacancy(reason, chat_name, link, text, event.message.date)

    return handler

async def folder_refresh_loop():
    global current_chat_ids

    while True:
        await asyncio.sleep(FOLDER_REFRESH_INTERVAL)

        print(f"\n🔄 Обновляю список чатов...")
        _, chat_ids = await load_chats_from_folder()

        if not chat_ids:
            print("   ⚠️  Не удалось получить список, попробую позже")
            continue

        new_ids = set(chat_ids) - current_chat_ids

        if new_ids:
            print(f"   ➕ Новых чатов: {len(new_ids)} — добавляю в мониторинг")
            client.add_event_handler(make_handler(), events.NewMessage(chats=list(new_ids)))
            current_chat_ids = set(chat_ids)
        else:
            print(f"   ✅ Новых чатов нет (всего: {len(chat_ids)})")

async def main():
    global current_chat_ids

    print("🔍 Загружаю чаты из папки...")
    entities, chat_ids = await load_chats_from_folder()

    if not entities:
        print("❌ Не удалось загрузить чаты, проверь FOLDER_INVITE")
        return

    current_chat_ids = set(chat_ids)
    print(f"✅ Загружено чатов: {len(entities)}")

    client.add_event_handler(make_handler(), events.NewMessage(chats=chat_ids))

    print("\n🚀 Мониторинг запущен!")
    print(f"   Ключевые слова: {KEYWORDS}")
    print(f"   Стоп-слов: {len(STOP_WORDS)}")
    print(f"   Обновление папки: каждые {FOLDER_REFRESH_INTERVAL // 60} мин")

    asyncio.ensure_future(folder_refresh_loop())
    await client.run_until_disconnected()

with client:
    client.loop.run_until_complete(main())
