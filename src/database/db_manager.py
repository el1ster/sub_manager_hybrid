import os
import json
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, joinedload
from cryptography.fernet import Fernet
from src.core.models import (Base, SystemSettings, Currency, Category, 
                               Subscription, Draft, DraftStatus, SyncQueue, SyncDirection)
from typing import List, Optional

class DBManager:
    """Менеджер для роботи з базою даних SQLite."""
    
    def __init__(self, db_path: str = "sub_manager.sqlite"):
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
        # TODO: Тут має бути шифрування AES. Поки що зберігаємо як JSON для прототипу.
        payload_data = {"event": event_type, "data": data}
        payload_json = json.dumps(payload_data, ensure_ascii=False)
        
        with self.get_session() as session:
            sync_item = SyncQueue(
                uuid=str(uuid.uuid4()),
                payload=payload_json, # В майбутньому: encrypt(payload_json)
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

    def approve_draft(self, draft_id: int, subscription: Subscription) -> None:
        with self.get_session() as session:
            draft = session.query(Draft).filter_by(id=draft_id).first()
            if draft:
                session.add(subscription)
                draft.status = DraftStatus.PROCESSED
                session.commit()

    def reject_draft(self, draft_id: int) -> None:
        with self.get_session() as session:
            draft = session.query(Draft).filter_by(id=draft_id).first()
            if draft:
                draft.status = DraftStatus.PROCESSED # Or maybe a REJECTED status
                session.commit()

# Глобальний екземпляр для зручності
db = DBManager()
