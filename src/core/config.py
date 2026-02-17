import os
from dotenv import load_dotenv
from pathlib import Path

# Завантаження змінних з .env файлу
load_dotenv()

class Config:
    """Централізована конфігурація проекту."""
    
    # Шляхи
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    SRC_DIR = BASE_DIR / "src"
    
    # БД
    DB_NAME = os.getenv("DB_NAME", "sub_manager.sqlite")
    DB_PATH = SRC_DIR / "server" / DB_NAME
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"
    
    # Telegram Bot
    BOT_TOKEN = os.getenv("BOT_TOKEN", "")
    
    # Налаштування додатка
    DEBUG = os.getenv("DEBUG", "True").lower() in ("true", "1", "t")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def validate(cls):
        """Перевірка критично важливих налаштувань."""
        if not cls.BOT_TOKEN and not cls.DEBUG:
            print("ПОПЕРЕДЖЕННЯ: BOT_TOKEN не встановлено. Бот не зможе запуститися.")
