import os
import json
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, joinedload
from cryptography.fernet import Fernet
from datetime import date, datetime
from src.core.config import Config
from src.core.models import (Base, SystemSettings, Currency, Category, 
                               Subscription, Draft, DraftStatus, SyncQueue, SyncDirection, PaymentHistory, SubscriptionState)
from typing import List, Optional

class DBManager:
    """Менеджер для роботи з базою даних SQLite."""
    
    def __init__(self, db_path: str = str(Config.DB_PATH)):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}", echo=False)
        self.Session = sessionmaker(bind=self.engine)
        
        # Ініціалізація БД
        self._initialize_db()

    def _initialize_db(self):
        """Створення таблиць та початкове заповнення даних."""
        # Увімкнення foreign keys для SQLite
        with self.engine.connect() as conn:
            conn.execute(text("PRAGMA foreign_keys = ON"))
        
        # Створення всіх таблиць на основі SQLAlchemy моделей
        Base.metadata.create_all(self.engine)
        
        # Перевірка та початкове заповнення (Seeding)
        with self.Session() as session:
            # 1. Генерація AES ключа, якщо його немає
            if not session.query(SystemSettings).filter_by(setting_key="enc_key").first():
                new_key = Fernet.generate_key().decode()
                session.add(SystemSettings(setting_key="enc_key", setting_value=new_key))
                session.add(SystemSettings(setting_key="pairing_status", setting_value="False"))
            
            # 2. Додавання базової валюти UAH та інших
            if not session.query(Currency).filter_by(code="UAH").first():
                session.add(Currency(code="UAH", manual_rate=1.0, is_base=True))
            
            if not session.query(Currency).filter_by(code="USD").first():
                session.add(Currency(code="USD", manual_rate=42.0, is_base=False))
                
            if not session.query(Currency).filter_by(code="EUR").first():
                session.add(Currency(code="EUR", manual_rate=45.5, is_base=False))
            
            # 3. Додавання базових категорій
            if not session.query(Category).first():
                default_categories = [
                    Category(name="Кіно та ТВ", icon_id="movie"),
                    Category(name="Музика", icon_id="music"),
                    Category(name="Робота / Софт", icon_id="work"),
                    Category(name="Ігри", icon_id="games"),
                    Category(name="Інше", icon_id="other")
                ]
                session.add_all(default_categories)
            
            session.commit()

    def get_session(self):
        """Повертає нову сесію БД."""
        return self.Session()

    # --- Currency Methods ---

    def get_currency_rate(self, code: str) -> float:
        """Повертає ручний курс валюти до UAH. Якщо валюта не знайдена, повертає 1.0."""
        if code == "UAH":
            return 1.0
        
        with self.get_session() as session:
            currency = session.query(Currency).filter_by(code=code).first()
            if currency:
                return currency.manual_rate
            return 1.0 # Fallback

    # --- Sync/Bot Feedback Methods ---

    def add_sync_event(self, event_type: str, data: dict):
        """Створює запис у черзі синхронізації (відповідь боту)."""
        payload_data = {"event": event_type, "data": data}
        payload_json = json.dumps(payload_data, ensure_ascii=False)
        
        with self.get_session() as session:
            enc_key_setting = session.query(SystemSettings).filter_by(setting_key="enc_key").first()
            if not enc_key_setting:
                print("[Security Error] Encryption key not found. Cannot encrypt sync event.")
                # Fallback to unencrypted or raise error based on desired security level
                encrypted_payload = payload_json.encode('utf-8') # Store unencrypted but encoded
            else:
                fernet = Fernet(enc_key_setting.setting_value.encode('utf-8'))
                encrypted_payload = fernet.encrypt(payload_json.encode('utf-8'))

            sync_item = SyncQueue(
                uuid=str(uuid.uuid4()),
                payload=encrypted_payload.decode('utf-8'), # Store as string
                direction=SyncDirection.TO_BOT
            )
            session.add(sync_item)
            session.commit()

    # --- Subscription CRUD ---

    def get_all_subscriptions(self) -> List[Subscription]:
        with self.get_session() as session:
            return session.query(Subscription).options(joinedload(Subscription.category)).all()

    def add_subscription(self, subscription: Subscription) -> None:
        with self.get_session() as session:
            session.add(subscription)
            session.commit()

    def update_subscription(self, sub_id: int, new_data: dict) -> None:
        with self.get_session() as session:
            session.query(Subscription).filter_by(id=sub_id).update(new_data)
            session.commit()

    def delete_subscription(self, sub_id: int) -> None:
        with self.get_session() as session:
            sub = session.query(Subscription).filter_by(id=sub_id).first()
            if sub:
                session.delete(sub)
                session.commit()
    
    # --- Category Methods ---

    def get_all_categories(self) -> List[Category]:
        with self.get_session() as session:
            return session.query(Category).all()

    # --- Draft Methods ---

    def get_pending_drafts(self) -> List[Draft]:
        with self.get_session() as session:
            return session.query(Draft).filter_by(status=DraftStatus.NEW).all()

    def get_draft_by_id(self, draft_id: int) -> Optional[Draft]:
        with self.get_session() as session:
            return session.query(Draft).filter_by(id=draft_id).first()

    def approve_draft(self, draft_id: int, subscription: Subscription) -> Optional[int]:
        with self.get_session() as session:
            draft = session.query(Draft).filter_by(id=draft_id).first()
            if draft:
                session.add(subscription)
                draft.status = DraftStatus.PROCESSED
                chat_id = draft.chat_id
                session.commit()
                return chat_id
            return None

    def reject_draft(self, draft_id: int) -> Optional[int]:
        with self.get_session() as session:
            draft = session.query(Draft).filter_by(id=draft_id).first()
            if draft:
                draft.status = DraftStatus.PROCESSED # Or maybe a REJECTED status
                chat_id = draft.chat_id
                session.commit()
                return chat_id
            return None

    # --- Payment History Methods ---

    def get_payment_history(self) -> List["PaymentHistory"]:
        """Повертає всю історію платежів, завантажуючи пов'язані підписки."""
        with self.get_session() as session:
            # Eagerly load the 'subscription' relationship to avoid lazy loading issues
            return session.query(PaymentHistory).options(joinedload(PaymentHistory.subscription)).order_by(PaymentHistory.pay_date.desc()).all()

    def mark_subscription_paid(self, sub_id: int, last_payment: date, next_payment: date, amount_paid: float):
        """Відзначає підписку як сплачену, оновлює дати та додає запис в історію."""
        with self.get_session() as session:
            subscription = session.query(Subscription).filter_by(id=sub_id).first()
            if subscription:
                subscription.last_payment = last_payment
                subscription.next_payment = next_payment
                subscription.state = SubscriptionState.ACTIVE # Установить статус на Активна
                subscription.is_reminder_sent = False # Сбросить флаг напоминания
                
                payment_record = PaymentHistory(
                    sub_id=sub_id,
                    final_sum=amount_paid,
                    pay_date=datetime.utcnow() # Use UTC now for consistency
                )
                session.add(payment_record)
                session.commit()

# Глобальний екземпляр для зручності
db = DBManager()
