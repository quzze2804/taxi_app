import os
import re
import json
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

router = Router()
TAXI_PHONE = "+380 75 443 67 57"
SUPPORT_USER = "@taxi_artsyz"
user_phones = {}

# ========== СИСТЕМА ПРОМОКОДІВ ==========
PROMO_FILE = "promocodes.json"
USER_PROMO_FILE = "user_promos.json"

promocodes = {}
user_promos = {}

class PromoStates(StatesGroup):
    waiting_for_promo = State()

def load_promocodes():
    global promocodes
    if os.path.exists(PROMO_FILE):
        try:
            with open(PROMO_FILE, 'r', encoding='utf-8') as f:
                promocodes = json.load(f)
        except:
            promocodes = {}
    else:
        promocodes = {
            "WELCOME10": {
                "discount": 10,
                "used_by": [],
                "max_uses": 100,
                "expires": "2025-12-31",
                "description": "10% знижка на перше замовлення"
            },
            "TAXI2024": {
                "discount": 15,
                "used_by": [],
                "max_uses": 50,
                "expires": "2025-12-31",
                "description": "15% знижка для нових клієнтів"
            }
        }
        save_promocodes()

def save_promocodes():
    with open(PROMO_FILE, 'w', encoding='utf-8') as f:
        json.dump(promocodes, f, ensure_ascii=False, indent=2)

def load_user_promos():
    global user_promos
    if os.path.exists(USER_PROMO_FILE):
        try:
            with open(USER_PROMO_FILE, 'r', encoding='utf-8') as f:
                user_promos = json.load(f)
                user_promos = {int(k): v for k, v in user_promos.items()}
        except:
            user_promos = {}

def save_user_promos():
    with open(USER_PROMO_FILE, 'w', encoding='utf-8') as f:
        json.dump(user_promos, f, ensure_ascii=False, indent=2)

def check_promo(code: str, user_id: int) -> dict:
    promo = promocodes.get(code.upper())
    if not promo:
        return {"valid": False, "message": "❌ Невірний промокод"}
    
    if promo.get("expires"):
        try:
            expires_date = datetime.strptime(promo["expires"], "%Y-%m-%d")
            if datetime.now() > expires_date:
                return {"valid": False, "message": "❌ Термін дії промокода закінчився"}
        except:
            pass
    
    if len(promo.get("used_by", [])) >= promo.get("max_uses", 999999):
        return {"valid": False, "message": "❌ Промокод більше не дійсний (вичерпано ліміт)"}
    
    if str(user_id) in promo.get("used_by", []):
        return {"valid": False, "message": "❌ Ви вже використовували цей промокод"}
    
    return {
        "valid": True,
        "discount": promo["discount"],
        "description": promo.get("description", "")
    }

def apply_promo(code: str, user_id: int) -> dict:
    promo = promocodes.get(code.upper())
    if not promo:
        return {"success": False, "message": "Невірний промокод"}
    
    if str(user_id) in promo.get("used_by", []):
        return {"success": False, "message": "Ви вже використовували цей промокод"}
    
    if len(promo.get("used_by", [])) >= promo.get("max_uses", 999999):
        return {"success": False, "message": "Ліміт використань промокода вичерпано"}
    
    if "used_by" not in promo:
        promo["used_by"] = []
    promo["used_by"].append(str(user_id))
    
    if user_id not in user_promos:
        user_promos[user_id] = []
    if code.upper() not in user_promos[user_id]:
        user_promos[user_id].append(code.upper())
    
    save_promocodes()
    save_user_promos()
    
    return {
        "success": True,
        "discount": promo["discount"],
        "message": f"✅ Промокод активовано! Ви отримали знижку {promo['discount']}%"
    }

def get_user_discount(user_id: int) -> int:
    if user_id not in user_promos:
        return 0
    max_discount = 0
    for code in user_promos[user_id]:
        if code in promocodes:
            discount = promocodes[code].get("discount", 0)
            if discount > max_discount:
                max_discount = discount
    return max_discount

# Завантажуємо дані
load_promocodes()
load_user_promos()
# ========================================

# --- Клавиатуры ---
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚕 Заказать такси")],
            [KeyboardButton(text="🎫 Ввести промокод"), KeyboardButton(text="💬 Поддержка")]
        ],
        resize_keyboard=True
    )

def get_share_contact_only():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Подтвердить номер телефона", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_quick_responses():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⏳ Уже выхожу")],
            [KeyboardButton(text="⏳ Буду через 5 минут")],
            [KeyboardButton(text="🚕 Я уже у машины")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def get_rating_keyboard(msg_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="1 ⭐", callback_data=f"rate_1_{msg_id}"),
             InlineKeyboardButton(text="2 ⭐", callback_data=f"rate_2_{msg_id}"),
             InlineKeyboardButton(text="3 ⭐", callback_data=f"rate_3_{msg_id}")],
            [InlineKeyboardButton(text="4 ⭐", callback_data=f"rate_4_{msg_id}"),
             InlineKeyboardButton(text="5 ⭐", callback_data=f"rate_5_{msg_id}")]
        ]
    )

# --- Обработчики ---
@router.message(Command("start"))
async def cmd_start(message: Message):
    args = message.text.split()
    if len(args) > 1:
        promo_code = args[1].upper()
        result = apply_promo(promo_code, message.from_user.id)
        if result["success"]:
            await message.answer(
                f"🎉 <b>Вітаємо!</b>\n\n{result['message']}\n\n"
                f"💰 <b>Ваша знижка:</b> {result['discount']}%\n\n"
                f"✨ <i>Знижка буде автоматично застосована при замовленні!</i>",
                parse_mode=ParseMode.HTML
            )
    
    await message.answer(
        f"✨ <b>Добро пожаловать в сервис такси Арциз!</b> ✨\n\n"
        f"🚕 <b>Ваш надежный способ передвижения по городу</b>\n\n"
        f"✓ <i>Быстрая подача автомобиля</i>\n"
        f"✓ <i>Вежливые водители</i>\n"
        f"✓ <i>Комфортные поездки</i>\n\n"
        f"📞 <b>Для заказа такси:</b>\n"
        f"• Нажмите кнопку <b>«Заказать такси»</b> в меню\n"
        f"• Или позвоните по номеру: <a href='tel:{TAXI_PHONE}'>{TAXI_PHONE}</a>\n\n"
        f"💫 <i>Желаем приятной поездки!</i>",
        reply_markup=get_main_menu(),
        parse_mode=ParseMode.HTML
    )

@router.message(Command("promo"))
async def show_promos(message: Message):
    active_promos = []
    for code, info in promocodes.items():
        if len(info.get("used_by", [])) < info.get("max_uses", 999999):
            active_promos.append(
                f"• <code>{code}</code> – знижка {info['discount']}%\n"
                f"  <i>{info.get('description', '')}</i>"
            )
    
    user_discount = get_user_discount(message.from_user.id)
    
    text = (
        f"🎫 <b>Доступні промокоди</b>\n\n"
        f"{chr(10).join(active_promos) if active_promos else 'Наразі немає активних промокодів'}\n\n"
        f"💰 <b>Ваша активна знижка:</b> {user_discount}%\n\n"
        f"📝 <i>Щоб активувати промокод, натисніть кнопку «Ввести промокод» в меню</i>"
    )
    await message.answer(text, parse_mode=ParseMode.HTML)

@router.message(F.text == "🎫 Ввести промокод")
async def enter_promo(message: Message, state: FSMContext):
    await message.answer(
        "🎫 <b>Введіть промокод</b>\n\n"
        "Напишіть код у повідомленні нижче.\n"
        "<i>Наприклад: WELCOME10</i>\n\n"
        "💡 <i>Промокод діє один раз на користувача</i>\n\n"
        "❌ <i>Щоб скасувати, натисніть /cancel</i>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(PromoStates.waiting_for_promo)

@router.message(PromoStates.waiting_for_promo, F.text)
async def process_promo(message: Message, state: FSMContext):
    promo_code = message.text.strip().upper()
    user_id = message.from_user.id
    
    result = apply_promo(promo_code, user_id)
    
    if result["success"]:
        await message.answer(
            f"🎉 <b>Вітаємо!</b>\n\n{result['message']}\n\n"
            f"💰 <b>Ваша знижка:</b> {result['discount']}%\n\n"
            f"✨ <i>Знижка буде автоматично застосована при наступному замовленні!</i>\n\n"
            f"🚕 <b>Готові замовити таксі?</b>",
            reply_markup=get_main_menu(),
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer(
            f"❌ <b>Помилка</b>\n\n{result['message']}\n\n"
            f"💡 <i>Перевірте правильність коду або спробуйте інший промокод</i>",
            reply_markup=get_main_menu(),
            parse_mode=ParseMode.HTML
        )
    await state.clear()

@router.message(Command("cancel"))
async def cancel_promo(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ <b>Введення промокоду скасовано</b>",
        reply_markup=get_main_menu(),
        parse_mode=ParseMode.HTML
    )

@router.message(F.contact)
async def handle_contact(message: Message, bot: Bot):
    user_phones[message.from_user.id] = message.contact.phone_number
    orders_chat_id = os.getenv('ORDERS_CHAT_ID')
    
    try:
        await bot.send_message(
            chat_id=orders_chat_id,
            text=f"📱 <b>Новый клиент зарегистрировался</b>\n"
                 f"👤 <b>Username:</b> @{message.from_user.username or 'не указан'}\n"
                 f"🆔 <b>ID:</b> <code>{message.from_user.id}</code>\n"
                 f"📞 <b>Телефон:</b> <a href='tel:{message.contact.phone_number}'>{message.contact.phone_number}</a>",
            parse_mode=ParseMode.HTML
        )
    except:
        pass

    await message.answer(
        "✅ <b>Номер телефона успешно подтвержден!</b>\n\n"
        "✨ <b>Что делать дальше:</b>\n"
        "1️⃣ Нажмите <b>«Заказать такси»</b> в меню\n"
        "2️⃣ Напишите ваш адрес (откуда и куда)\n\n"
        "<i>Например: ул. Соборная 15 до ЖД вокзала</i>\n\n"
        "🚕 <b>Ваш заказ будет принят мгновенно!</b>",
        reply_markup=get_main_menu(),
        parse_mode=ParseMode.HTML
    )

@router.message(F.text & ~F.text.startswith("/"))
async def process_text_input(message: Message, bot: Bot):
    if message.text == "💬 Поддержка":
        await message.answer(
            f"📞 <b>Служба поддержки</b>\n\n"
            f"Свяжитесь с нашим администратором: {SUPPORT_USER}\n"
            f"Или позвоните: <a href='tel:{TAXI_PHONE}'>{TAXI_PHONE}</a>\n\n"
            f"<i>Мы всегда рады помочь вам! 💫</i>",
            parse_mode=ParseMode.HTML
        )
        return

    if message.text == "🚕 Заказать такси":
        if message.from_user.id not in user_phones:
            await message.answer(
                "📱 <b>Для оформления заказа необходимо подтвердить ваш номер телефона</b>\n\n"
                "Пожалуйста, нажмите кнопку ниже, чтобы поделиться контактом: 👇",
                reply_markup=get_share_contact_only(),
                parse_mode=ParseMode.HTML
            )
        else:
            user_discount = get_user_discount(message.from_user.id)
            discount_text = f"\n\n💰 <b>Ваша знижка:</b> {user_discount}%" if user_discount else ""
            
            await message.answer(
                f"🚕 <b>Оформление заказа</b>\n\n"
                f"Пожалуйста, напишите <b>откуда и куда</b> вас нужно отвезти.\n\n"
                f"<i>Пример: ул. Соборная 10 до ЖД вокзала</i>\n\n"
                f"📞 <i>Или сделайте заказ по телефону:</i> <a href='tel:{TAXI_PHONE}'>{TAXI_PHONE}</a>"
                f"{discount_text}",
                parse_mode=ParseMode.HTML
            )
        return

    quick_texts = ["⏳ Уже выхожу", "⏳ Буду через 5 минут", "🚕 Я уже у машины"]
    if message.text in quick_texts:
        orders_chat_id = os.getenv('ORDERS_CHAT_ID')
        user_info = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
        
        await bot.send_message(
            chat_id=orders_chat_id,
            text=f"🔔 <b>Статус от клиента</b> {user_info}:\n💬 <i>{message.text}</i>",
            parse_mode=ParseMode.HTML
        )
        await message.answer(
            "✅ <b>Сообщение передано водителю!</b>",
            reply_markup=get_main_menu(),
            parse_mode=ParseMode.HTML
        )
        return

    if message.from_user.id not in user_phones:
        await message.answer(
            "📱 <b>Сначала необходимо подтвердить номер телефона</b>\n\n"
            "Пожалуйста, нажмите кнопку ниже: 👇",
            reply_markup=get_share_contact_only(),
            parse_mode=ParseMode.HTML
        )
        return

    orders_chat_id = os.getenv('ORDERS_CHAT_ID')
    phone = user_phones.get(message.from_user.id)
    user_info = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
    
    user_discount = get_user_discount(message.from_user.id)
    discount_text = f"\n🎫 <b>Знижка клієнта:</b> {user_discount}%" if user_discount else ""
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Принять заказ", callback_data=f"accept_{message.chat.id}")
        ]]
    )
    
    order_text = (
        f"🚨 <b>НОВЫЙ ЗАКАЗ!</b> 🚨\n\n"
        f"👤 <b>Клиент:</b> {user_info}\n"
        f"📞 <b>Телефон:</b> <a href='tel:{phone}'>{phone}</a>\n"
        f"📍 <b>Маршрут:</b>\n"
        f"<code>{message.text}</code>\n"
        f"{discount_text}\n\n"
        f"🆔 <b>ID заказа:</b> <code>{message.chat.id}</code>\n"
        f"⏱ <b>Время заказа:</b> {__import__('datetime').datetime.now().strftime('%H:%M:%S')}\n\n"
        f"➖➖➖➖➖➖➖➖➖➖\n"
        f"<i>Нажмите «Принять заказ» чтобы начать поездку</i>"
    )
    
    await bot.send_message(
        chat_id=orders_chat_id,
        text=order_text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML
    )
    
    discount_info = f"\n\n🎫 <b>Ваша знижка:</b> {user_discount}%" if user_discount else ""
    
    await message.answer(
        f"✅ <b>Ваш заказ принят!</b> 🚕\n\n"
        f"✨ <b>Что происходит сейчас:</b>\n"
        f"• Мы ищем ближайшего свободного водителя\n"
        f"• Как только машина найдена - вы получите уведомление\n"
        f"{discount_info}\n\n"
        f"📞 <i>Вопросы:</i> <a href='tel:{TAXI_PHONE}'>{TAXI_PHONE}</a>",
        parse_mode=ParseMode.HTML
    )

# ========== АДМІН-КОМАНДИ ==========
ADMIN_IDS = [123456789]  # ⚠️ ЗАМІНИ НА СВІЙ TELEGRAM ID!

@router.message(Command("addpromo"))
async def add_promo(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас немає прав для цієї команди", parse_mode=ParseMode.HTML)
        return
    
    args = message.text.split(maxsplit=5)
    if len(args) < 3:
        await message.answer(
            "📝 <b>Формат команди:</b>\n\n"
            "<code>/addpromo КОД ЗНИЖКА МАКС_ВИКОРИСТАНЬ [ДАТА] [ОПИС]</code>\n\n"
            "<b>Приклади:</b>\n"
            "<code>/addpromo SUMMER50 50 100</code>\n"
            "<code>/addpromo AUTUMN20 20 50 2025-12-31</code>\n\n"
            "<i>📅 Формат дати: РРРР-ММ-ДД</i>",
            parse_mode=ParseMode.HTML
        )
        return
    
    code = args[1].upper()
    discount = int(args[2])
    max_uses = int(args[3])
    expires = args[4] if len(args) > 4 else "2026-12-31"
    description = args[5] if len(args) > 5 else f"Акційна знижка {discount}%"
    
    promocodes[code] = {
        "discount": discount,
        "used_by": [],
        "max_uses": max_uses,
        "expires": expires,
        "description": description
    }
    save_promocodes()
    
    await message.answer(
        f"✅ <b>Промокод створено!</b>\n\n"
        f"🎫 <code>{code}</code>\n"
        f"💰 {discount}% | 📊 {max_uses} використань\n"
        f"📅 до {expires}\n\n"
        f"🔗 <code>https://t.me/TaxiArcyzBot?start={code}</code>",
        parse_mode=ParseMode.HTML
    )

@router.message(Command("listpromo"))
async def list_promos_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас немає прав для цієї команди", parse_mode=ParseMode.HTML)
        return
    
    if not promocodes:
        await message.answer("📭 Немає активних промокодів", parse_mode=ParseMode.HTML)
        return
    
    text = "📋 <b>Список промокодів</b>\n\n"
    for code, info in promocodes.items():
        used = len(info.get("used_by", []))
        max_uses = info.get("max_uses", "∞")
        text += f"🎫 <code>{code}</code> | {info['discount']}% | {used}/{max_uses}\n"
    
    await message.answer(text, parse_mode=ParseMode.HTML)

@router.message(Command("deletepromo"))
async def delete_promo(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ У вас немає прав для цієї команди", parse_mode=ParseMode.HTML)
        return
    
    args = message.text.split()
    if len(args) < 2:
        await message.answer("📝 <code>/deletepromo КОД</code>", parse_mode=ParseMode.HTML)
        return
    
    code = args[1].upper()
    if code not in promocodes:
        await message.answer(f"❌ Промокод <code>{code}</code> не знайдено", parse_mode=ParseMode.HTML)
        return
    
    del promocodes[code]
    save_promocodes()
    await message.answer(f"✅ <b>Промокод <code>{code}</code> видалено!</b>", parse_mode=ParseMode.HTML)

# ❗️ НЕТ ОБРАБОТЧИКА F.location - он удален, чтобы не конфликтовать с driver.py

@router.callback_query(F.data.startswith("rate_"))
async def process_rating(callback: CallbackQuery, bot: Bot):
    data = callback.data.split("_")
    await callback.answer("✨ Спасибо за вашу оценку!")
    
    if len(data) < 3:
        return
    
    rating, order_msg_id = data[1], int(data[2])
    orders_chat_id = os.getenv('ORDERS_CHAT_ID')
    
    rating_messages = {
        "1": "😞 Очень низкая оценка. Обязательно разберемся с ситуацией",
        "2": "😕 Низкая оценка. Мы работаем над улучшением сервиса",
        "3": "😐 Средняя оценка. Расскажите, что можно улучшить?",
        "4": "🙂 Хорошая оценка! Рады, что вам понравилось",
        "5": "🌟 Отлично! Спасибо за высокую оценку нашего сервиса!"
    }
    
    await callback.message.edit_text(
        f"✨ <b>Благодарим за обратную связь!</b>\n\n"
        f"⭐ <b>Ваша оценка:</b> {rating}\n\n"
        f"{rating_messages.get(rating, 'Спасибо!')}\n\n"
        f"<i>Мы становимся лучше благодаря вам! 💫</i>",
        parse_mode=ParseMode.HTML
    )
    
    try:
        await bot.send_message(
            chat_id=orders_chat_id,
            text=f"⭐ <b>Новая оценка поездки:</b> {rating}\n"
                 f"{rating_messages.get(rating, '')}",
            reply_to_message_id=order_msg_id,
            parse_mode=ParseMode.HTML
        )
    except:
        await bot.send_message(
            chat_id=orders_chat_id,
            text=f"⭐ <b>Оценка поездки:</b> {rating}",
            parse_mode=ParseMode.HTML
        )