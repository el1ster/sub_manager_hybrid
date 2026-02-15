from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, Date, ForeignKey, Boolean, Enum, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
import enum

# --- Переліки (Enums) ---

class SubscriptionState(enum.Enum):
    ACTIVE = "Active"
    WAITING_BOT = "Waiting_Bot"
    OVERDUE = "Overdue"

class SyncDirection(enum.Enum):
    TO_BOT = "To_Bot"
    FROM_BOT = "From_Bot"

class PaymentType(enum.Enum):
    AUTO = "Auto"
    MANUAL = "Manual"

class DraftStatus(enum.Enum):
    NEW = "New"
    PROCESSED = "Processed"

# --- Базовий клас ---

class Base(DeclarativeBase):
    """Базовий клас для моделей SQLAlchemy."""
    pass

# --- 1. Технічний блок ---

class SystemSettings(Base):
    """Налаштування системи (Key-Value)."""
    __tablename__ = "system_settings"
    
    setting_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    setting_value: Mapped[str] = mapped_column(Text)

class SyncQueue(Base):
    """Буфер обміну з ботом (Черга синхронізації)."""
    __tablename__ = "sync_queue"
    
    uuid: Mapped[str] = mapped_column(String(36), primary_key=True)
    payload: Mapped[str] = mapped_column(Text)  # Зашифрований AES-256 JSON
    direction: Mapped[SyncDirection] = mapped_column(Enum(SyncDirection))
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

# --- 2. Довідковий блок ---

class Category(Base):
    """Довідник категорій підписок."""
    __tablename__ = "categories"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    icon_id: Mapped[str] = mapped_column(String(50))  # ID іконки для PySide6
    
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="category")

class Currency(Base):
    """Довідник валют та курсів."""
    __tablename__ = "currencies"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(3), unique=True)  # UAH, USD, NOK
    manual_rate: Mapped[float] = mapped_column(Float)  # Курс до гривні
    is_base: Mapped[bool] = mapped_column(Boolean, default=False)

# --- 3. Операційний блок ---

class Subscription(Base):
    """Основний реєстр підписок."""
    __tablename__ = "subscriptions"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    cost_uah: Mapped[float] = mapped_column(Float)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"))
    period: Mapped[str] = mapped_column(String(50))  # Місяць/Квартал/Рік
    last_payment: Mapped[date] = mapped_column(Date)
    next_payment: Mapped[date] = mapped_column(Date)
    payment_type: Mapped[PaymentType] = mapped_column(Enum(PaymentType), default=PaymentType.AUTO)
    state: Mapped[SubscriptionState] = mapped_column(Enum(SubscriptionState), default=SubscriptionState.ACTIVE)
    
    category: Mapped["Category"] = relationship(back_populates="subscriptions")
    history: Mapped[list["PaymentHistory"]] = relationship(back_populates="subscription")

class Draft(Base):
    """Карантин заявок з Telegram."""
    __tablename__ = "drafts"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    raw_name: Mapped[str] = mapped_column(String(255))
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[DraftStatus] = mapped_column(Enum(DraftStatus), default=DraftStatus.NEW)

class PaymentHistory(Base):
    """Архів транзакцій (для статистики)."""
    __tablename__ = "payment_history"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    sub_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id"))
    final_sum: Mapped[float] = mapped_column(Float)
    pay_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    subscription: Mapped["Subscription"] = relationship(back_populates="history")
