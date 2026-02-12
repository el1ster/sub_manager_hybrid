import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from cryptography.fernet import Fernet
from src.core.models import Base, SystemSettings, Currency, Category

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
            
            # 2. Додавання базової валюти UAH
            if not session.query(Currency).filter_by(code="UAH").first():
                session.add(Currency(code="UAH", manual_rate=1.0, is_base=True))
            
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

# Глобальний екземпляр для зручності
db = DBManager()
