import os
import json
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile
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
    return {"valid": True, "discount": promo["discount"], "description": promo.get("description", "")}

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
    return {"success": True, "discount": promo["discount"], "message": f"✅ Промокод активовано! Ви отримали знижку {promo['discount']}%"}

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

load_promocodes()
load_user_promos()
# ========================================

# Состояния для заказа
class OrderStates(StatesGroup):
    waiting_for_pickup = State()
    waiting_for_destination = State()
    confirming_order = State()

# --- Клавиатуры ---
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🚕 Заказать такси")],
            [KeyboardButton(text="🎫 Ввести промокод"), KeyboardButton(text="💬 Поддержка")]
        ],
        resize_keyboard=True
    )

def get_order_in_progress_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отменить заказ")],
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
# Быстрые ответы (должны работать всегда)
@router.message(F.text.in_(["⏳ Уже выхожу", "⏳ Буду через 5 минут", "🚕 Я уже у машины"]))
async def quick_reply(message: Message, bot: Bot, state: FSMContext):
    orders_chat_id = os.getenv('ORDERS_CHAT_ID')
    user_info = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
    
    await bot.send_message(
        chat_id=orders_chat_id,
        text=f"🔔 <b>Статус от клиента</b> {user_info}:\n💬 <i>{message.text}</i>",
        parse_mode=ParseMode.HTML
    )
    
    current_state = await state.get_state()
    if current_state and current_state.startswith("OrderStates"):
        reply_markup = get_order_in_progress_menu()
    else:
        reply_markup = get_main_menu()
    
    await message.answer(
        "✅ <b>Сообщение передано водителю!</b>",
        reply_markup=reply_markup,
        parse_mode=ParseMode.HTML
    )

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
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
    
    photo_path = "BOT_TAXI/welcome.jpg"
    caption = (
        f"✨ <b>Добро пожаловать в сервис такси Арциз!</b> ✨\n\n"
        f"🚕 <b>Ваш надежный способ передвижения по городу</b>\n\n"
        f"✓ <i>Быстрая подача автомобиля</i>\n"
        f"✓ <i>Вежливые водители</i>\n"
        f"✓ <i>Комфортные поездки</i>\n\n"
        f"📞 <b>Для заказа такси:</b>\n"
        f"• Нажмите кнопку <b>«Заказать такси»</b> в меню\n"
        f"• Или позвоните по номеру: <a href='tel:{TAXI_PHONE}'>{TAXI_PHONE}</a>\n\n"
        f"💫 <i>Желаем приятной поездки!</i>"
    )
    
    if os.path.exists(photo_path):
        await message.answer_photo(
            photo=FSInputFile(photo_path),
            caption=caption,
            reply_markup=get_main_menu(),
            parse_mode=ParseMode.HTML
        )
    else:
        await message.answer(
            caption,
            reply_markup=get_main_menu(),
            parse_mode=ParseMode.HTML
        )

@router.message(Command("promo"))
async def show_promos(message: Message):
    active_promos = []
    for code, info in promocodes.items():
        if len(info.get("used_by", [])) < info.get("max_uses", 999999):
            active_promos.append(
                f"• <code>{code}</code> – знижка {info['discount']}%\n  <i>{info.get('description', '')}</i>"
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
        "Напишіть код у повідомленні ниже.\n"
        "<i>Наприклад: WELCOME10</i>\n\n"
        "❌ <i>Щоб скасувати, натисніть /cancel</i>",
        parse_mode=ParseMode.HTML
    )
    await state.set_state(PromoStates.waiting_for_promo)

@router.message(PromoStates.waiting_for_promo, F.text)
async def process_promo(message: Message, state: FSMContext):
    promo_code = message.text.strip().upper()
    result = apply_promo(promo_code, message.from_user.id)
    if result["success"]:
        await message.answer(
            f"🎉 <b>Вітаємо!</b>\n\n{result['message']}\n\n"
            f"💰 <b>Ваша знижка:</b> {result['discount']}%\n\n"
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
        "2️⃣ Напишите ваш адрес (откуда и куда)",
        reply_markup=get_main_menu(),
        parse_mode=ParseMode.HTML
    )

# ========== FSM ЗАКАЗА ==========
@router.message(F.text == "🚕 Заказать такси")
async def order_taxi(message: Message, state: FSMContext):
    if message.from_user.id not in user_phones:
        await message.answer(
            "📱 <b>Для оформления заказа необходимо подтвердить ваш номер телефона</b>",
            reply_markup=get_share_contact_only(),
            parse_mode=ParseMode.HTML
        )
        return
    await state.set_state(OrderStates.waiting_for_pickup)
    await message.answer(
        "📍 <b>Откуда вас забрать?</b>\n\n"
        "Напишите адрес или отправьте геолокацию.\n<i>Пример: ул. Соборная 15</i>",
        reply_markup=get_order_in_progress_menu(),
        parse_mode=ParseMode.HTML
    )

@router.message(OrderStates.waiting_for_pickup, F.text)
@router.message(OrderStates.waiting_for_pickup, F.location)
async def get_pickup(message: Message, state: FSMContext):
    pickup_data = {}
    if message.location:
        pickup_data["address"] = "📍 По геолокации"
        pickup_data["lat"] = message.location.latitude
        pickup_data["lon"] = message.location.longitude
        await message.answer(
            "✅ Геолокація отримана.\nТепер напишіть, <b>куди їдемо</b>:",
            reply_markup=get_order_in_progress_menu(),
            parse_mode=ParseMode.HTML
        )
    else:
        pickup_data["address"] = message.text
        await message.answer(
            f"✅ Адрес отправления: {message.text}\n\nТеперь напишите <b>куда едем</b>:",
            reply_markup=get_order_in_progress_menu(),
            parse_mode=ParseMode.HTML
        )
    await state.update_data(pickup=pickup_data)
    await state.set_state(OrderStates.waiting_for_destination)

@router.message(OrderStates.waiting_for_destination, F.text)
async def get_destination(message: Message, state: FSMContext):
    data = await state.get_data()
    pickup = data.get("pickup", {})
    destination = message.text
    await state.update_data(destination={"address": destination})
    
    confirm_text = (
        f"🚕 <b>Ваш заказ:</b>\n"
        f"📍 Откуда: {pickup.get('address', '?')}\n"
        f"🏁 Куда: {destination}\n\n"
        f"✅ Подтверждаете?"
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Да", callback_data="confirm_order"),
         InlineKeyboardButton(text="❌ Нет", callback_data="cancel_order")]
    ])
    await message.answer(confirm_text, reply_markup=keyboard, parse_mode=ParseMode.HTML)
    await state.set_state(OrderStates.confirming_order)

@router.callback_query(OrderStates.confirming_order, F.data == "confirm_order")
async def confirm_order(callback: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    pickup = data.get("pickup", {})
    destination = data.get("destination", {})
    user_id = callback.from_user.id
    phone = user_phones.get(user_id)
    user_info = f"@{callback.from_user.username}" if callback.from_user.username else f"ID:{user_id}"
    discount = get_user_discount(user_id)
    discount_text = f"\n🎫 Знижка: {discount}%" if discount else ""

    order_text = (
        f"🚨 <b>НОВЫЙ ЗАКАЗ!</b> 🚨\n"
        f"👤 {user_info}\n"
        f"📞 <a href='tel:{phone}'>{phone}</a>\n"
        f"📍 Откуда: {pickup.get('address', '?')}\n"
        f"🏁 Куда: {destination.get('address', '?')}\n"
        f"{discount_text}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"⏱ {datetime.now().strftime('%H:%M:%S')}"
    )
    orders_chat_id = os.getenv('ORDERS_CHAT_ID')
    await bot.send_message(
        orders_chat_id,
        order_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="✅ Принять заказ", callback_data=f"accept_{user_id}")
        ]]),
        parse_mode=ParseMode.HTML
    )
    await callback.message.edit_text(
        "✅ Заказ отправлен! Ищем водителя...\n🚕 Ожидайте.",
        reply_markup=None
    )
    await callback.message.answer("🔝 Главное меню", reply_markup=get_main_menu())
    await state.clear()
    await callback.answer()

@router.callback_query(OrderStates.confirming_order, F.data == "cancel_order")
async def cancel_order(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("❌ Заказ отменён.")
    await callback.message.answer("🔝 Главное меню", reply_markup=get_main_menu())
    await callback.answer()

@router.message(F.text == "❌ Отменить заказ")
async def cancel_order_button(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Заказ отменён.", reply_markup=get_main_menu(), parse_mode=ParseMode.HTML)

@router.message(F.text == "💬 Поддержка")
async def support(message: Message):
    await message.answer(
        f"📞 <b>Служба поддержки</b>\n\n"
        f"Админ: {SUPPORT_USER}\n"
        f"Звоните: <a href='tel:{TAXI_PHONE}'>{TAXI_PHONE}</a>",
        parse_mode=ParseMode.HTML
    )

@router.callback_query(F.data.startswith("rate_"))
async def process_rating(callback: CallbackQuery, bot: Bot):
    data = callback.data.split("_")
    await callback.answer("Спасибо за оценку!")
    if len(data) < 3:
        return
    rating = data[1]
    msg_id = int(data[2])
    orders_chat_id = os.getenv('ORDERS_CHAT_ID')
    await callback.message.edit_text(f"⭐ Спасибо за оценку {rating}!")
    try:
        await bot.send_message(orders_chat_id, f"⭐ Оценка поездки: {rating}", reply_to_message_id=msg_id)
    except:
        await bot.send_message(orders_chat_id, f"⭐ Оценка поездки: {rating}")