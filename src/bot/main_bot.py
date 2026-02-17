import asyncio
import logging
import sys
import os
import json
from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from sqlalchemy import create_engine, select, delete
from sqlalchemy.orm import sessionmaker
from cryptography.fernet import Fernet

# --- Path Setup ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
sys.path.insert(0, project_root)

from src.core.models import SyncQueue, SyncDirection, Draft, SystemSettings
from src.database.db_manager import DBManager

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Config ---
TOKEN = os.getenv("BOT_TOKEN")
DB_PATH = os.path.abspath(os.path.join(project_root, "src", "server", "sub_manager.sqlite"))

if not TOKEN:
    logger.error("BOT_TOKEN not found in environment variables!")
    sys.exit(1)

# --- Database ---
db_manager = DBManager(db_path=DB_PATH)
Session = db_manager.get_session

# --- Bot Setup ---
# Initialize Bot with DefaultBotProperties for parse_mode
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()
dp.include_router(router)

# --- FSM States ---
class AddSub(StatesGroup):
    waiting_for_name = State()
    waiting_for_amount = State()
    waiting_for_currency = State()

# --- Helper Functions ---
def get_linked_chat_id():
    """Returns the linked chat ID from the database as int or None."""
    with Session() as session:
        setting = session.query(SystemSettings).filter_by(setting_key="linked_chat_id").first()
        if setting and setting.setting_value:
            try:
                return int(setting.setting_value)
            except ValueError:
                return None
    return None

# --- Handlers ---

@router.message(Command("start"))
async def cmd_start(message: types.Message):
    linked_id = get_linked_chat_id()
    user_name = message.from_user.first_name or "Користувач"
    
    if linked_id == message.chat.id:
        # Scenario: Connected and Authorized
        await message.answer(
            f"👋 <b>Вітаю, {user_name}!</b>\n\n"
            "✅ Бот успішно підключено до вашого ПК.\n"
            "Ви можете додавати нові підписки за допомогою команди /add."
        )
    elif linked_id is None:
        # Scenario: Not Connected to ANY PC
        await message.answer(
            f"👋 <b>Вітаю, {user_name}!</b>\n\n"
            "⛔️ <b>Бот наразі не підключено до жодного ПК.</b>\n\n"
            "Щоб розпочати роботу, вам потрібно виконати спарювання:\n"
            "1. Відкрийте вкладку 'Налаштування' у програмі на комп'ютері.\n"
            "2. Натисніть 'Згенерувати код'.\n"
            "3. Надішліть сюди команду: <code>/pair КОД</code>"
        )
    else:
        # Scenario: Connected to SOMEONE ELSE
        await message.answer(
            f"👋 <b>Вітаю, {user_name}!</b>\n\n"
            "⚠️ <b>Доступ обмежено.</b>\n"
            "Цей бот вже прив'язаний до іншого користувача.\n"
            "Якщо це ваша копія бота, будь ласка, відв'яжіть старий акаунт у налаштуваннях десктопного додатка."
        )

@router.message(Command("pair"))
async def cmd_pair(message: types.Message):
    """Pair the bot with the Desktop application using a code."""
    linked_id = get_linked_chat_id()
    
    if linked_id == message.chat.id:
        await message.answer("✅ Ви вже підключені! Використовуйте /add.")
        return
    
    if linked_id is not None:
        await message.answer("⛔️ Бот вже прив'язаний до іншого пристрою. Спочатку відв'яжіть його в налаштуваннях десктопа.")
        return

    try:
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2:
            raise ValueError
        code = parts[1].strip()
        if not code.isdigit() or len(code) != 6:
            raise ValueError
    except (IndexError, ValueError):
        await message.answer("❌ <b>Помилка формату.</b>\nВикористання: <code>/pair 123456</code>")
        return

    payload = {
        "event": "pairing_request",
        "code": code,
        "chat_id": message.chat.id
    }
    
    with Session() as session:
        import uuid
        from datetime import datetime

        enc_key_setting = session.query(SystemSettings).filter_by(setting_key="enc_key").first()
        if not enc_key_setting:
            await message.answer("❌ Помилка безпеки: ключ шифрування не знайдено на сервері.")
            return
        
        fernet = Fernet(enc_key_setting.setting_value.encode('utf-8'))
        encrypted_payload = fernet.encrypt(json.dumps(payload, ensure_ascii=False).encode('utf-8'))

        sync_item = SyncQueue(
            uuid=str(uuid.uuid4()),
            payload=encrypted_payload.decode('utf-8'),
            direction=SyncDirection.FROM_BOT,
            timestamp=datetime.utcnow()
        )
        session.add(sync_item)
        session.commit()
    
    await message.answer("🔄 Запит на підключення надіслано...")

@router.message(Command("add"))
async def cmd_add(message: types.Message, state: FSMContext):
    linked_id = get_linked_chat_id()
    
    # Strict Authorization Check
    if linked_id != message.chat.id:
        if linked_id is None:
             await message.answer("⛔️ <b>Помилка доступу.</b>\nСпочатку виконайте спарювання через <code>/pair КОД</code>.")
        else:
             await message.answer("⛔️ <b>Доступ заборонено.</b>\nБот прив'язаний до іншого користувача.")
        return

    await message.answer("📝 Введіть назву підписки (наприклад, Netflix):")
    await state.set_state(AddSub.waiting_for_name)

@router.message(AddSub.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("💰 Введіть вартість (тільки число, наприклад 12.99):")
    await state.set_state(AddSub.waiting_for_amount)

@router.message(AddSub.waiting_for_amount)
async def process_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text.replace(",", "."))
        if amount <= 0: raise ValueError
        
        await state.update_data(amount=amount)
        
        # Inline Keyboard for Currency
        builder = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🇺🇦 UAH", callback_data="currency_UAH")],
            [InlineKeyboardButton(text="🇺🇸 USD", callback_data="currency_USD"), 
             InlineKeyboardButton(text="🇪🇺 EUR", callback_data="currency_EUR")]
        ])
        
        await message.answer("💱 Оберіть валюту:", reply_markup=builder)
        await state.set_state(AddSub.waiting_for_currency)
        
    except ValueError:
        await message.answer("❌ Будь ласка, введіть коректне позитивне число.")

@router.callback_query(AddSub.waiting_for_currency, F.data.startswith("currency_"))
async def process_currency(callback: types.CallbackQuery, state: FSMContext):
    currency = callback.data.split("_")[1]
    data = await state.get_data()
    
    payload = {
        "raw_name": data['name'],
        "amount": data['amount'],
        "currency": currency,
        "chat_id": callback.message.chat.id
    }
    
    with Session() as session:
        import uuid
        from datetime import datetime

        enc_key_setting = session.query(SystemSettings).filter_by(setting_key="enc_key").first()
        if not enc_key_setting:
            await callback.message.edit_text("❌ Помилка безпеки: ключ шифрування не знайдено на сервері.")
            await state.clear()
            return

        fernet = Fernet(enc_key_setting.setting_value.encode('utf-8'))
        encrypted_payload = fernet.encrypt(json.dumps(payload, ensure_ascii=False).encode('utf-8'))

        sync_item = SyncQueue(
            uuid=str(uuid.uuid4()),
            payload=encrypted_payload.decode('utf-8'),
            direction=SyncDirection.FROM_BOT,
            timestamp=datetime.utcnow()
        )
        session.add(sync_item)
        session.commit()
        
    await callback.message.edit_text(
        f"✅ Заявку створено!\n"
        f"<b>{data['name']}</b>: {data['amount']} {currency}\n"
        f"Очікуйте підтвердження на ПК."
    )
    await state.clear()

# --- Background Task: Check for Feedback (TO_BOT) ---

async def check_feedback_queue():
    """Background task to poll SyncQueue for messages from Desktop."""
    while True:
        try:
            with Session() as session:
                # Find messages for bot
                stmt = select(SyncQueue).where(SyncQueue.direction == SyncDirection.TO_BOT).limit(5)
                messages = session.execute(stmt).scalars().all()
                
                for msg in messages:
                    try:
                        enc_key_setting = session.query(SystemSettings).filter_by(setting_key="enc_key").first()
                        if not enc_key_setting:
                            logger.error("Encryption key not found. Cannot decrypt sync event.")
                            session.delete(msg) # Remove problematic message
                            continue
                        
                        fernet = Fernet(enc_key_setting.setting_value.encode('utf-8'))
                        
                        try:
                            decrypted_payload = fernet.decrypt(msg.payload.encode('utf-8')).decode('utf-8')
                            data = json.loads(decrypted_payload)
                        except Exception as e:
                            logger.error(f"Failed to decrypt or parse payload for msg {msg.uuid}: {e}")
                            session.delete(msg) # Remove problematic message
                            continue
                        
                        event = data.get("event")
                        details = data.get("data", {})
                        
                        logger.info(f"📨 Feedback received: {event} - {details}")
                        
                        chat_id = details.get("chat_id")
                        if chat_id:
                            try:
                                if event == "subscription_approved":
                                    await bot.send_message(
                                        chat_id,
                                        f"✅ Вашу заявку <b>{details.get('original_draft')}</b> схвалено!\n"
                                        f"Додано як: <b>{details.get('new_name')}</b> ({details.get('cost_uah')} UAH)"
                                    )
                                elif event == "pairing_success":
                                    await bot.send_message(
                                        chat_id,
                                        "✅ <b>Успішно підключено!</b>\nТепер ви можете додавати підписки через /add."
                                    )
                                elif event == "pairing_failed":
                                    await bot.send_message(
                                        chat_id,
                                        "❌ <b>Помилка підключення.</b>\nПеревірте код та спробуйте ще раз."
                                    )
                                elif event == "error_not_paired":
                                    await bot.send_message(
                                        chat_id,
                                        "⛔️ <b>Ваша заявка відхилена.</b>\nВикористайте <code>/pair КОД</code> для підключення до десктопа."
                                    )
                                elif event == "draft_rejected":
                                    await bot.send_message(
                                        chat_id,
                                        f"❌ Вашу заявку (ID: {details.get('draft_id')}) відхилено."
                                    )
                                elif event == "draft_received":
                                    await bot.send_message(
                                        chat_id,
                                        f"📥 Сервер отримав заявку: <b>{details.get('name')}</b>\n"
                                        f"Присвоєно ID: <b>{details.get('draft_id')}</b>"
                                    )
                                elif event == "payment_reminder":
                                    await bot.send_message(
                                        chat_id,
                                        f"🗓️ <b>Нагадування про платіж</b>\n\n"
                                        f"Скоро потрібно сплатити за підписку: <b>{details.get('name')}</b>\n"
                                        f"<b>Сума:</b> {details.get('cost_uah')} UAH\n"
                                        f"<b>Дата списання:</b> {details.get('next_payment')}"
                                    )
                            except Exception as e:
                                logger.error(f"Failed to send notification to {chat_id}: {e}")
                        
                        # Remove from queue
                        session.delete(msg)
                        
                    except Exception as e:
                        logger.error(f"Error processing sync message {msg.uuid}: {e}")
                
                if messages:
                    session.commit()
                    
        except Exception as e:
            logger.error(f"Database error in feedback loop: {e}")
            
        await asyncio.sleep(5)

# --- Main Entry ---

async def main():
    logger.info("🤖 Starting Bot...")
    asyncio.create_task(check_feedback_queue())
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped")
