from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from PySide6.QtGui import QBrush, QColor # Добавлен импорт для цветов
from typing import List, Any
from src.core.models import Subscription, SubscriptionState, PaymentType
from datetime import datetime, date

class SubscriptionTableModel(QAbstractTableModel):
    """Модель для відображення підписок у QTableView."""

    _payment_type_map = {
        PaymentType.AUTO: "Автоматично",
        PaymentType.MANUAL: "Вручну",
    }

    _state_map = {
        SubscriptionState.ACTIVE: "Активна",
        SubscriptionState.WAITING_BOT: "Очікує підтвердження",
        SubscriptionState.OVERDUE: "Прострочена",
    }

    def __init__(self, data: List[Subscription] = None):
        super().__init__()
        self._data = data or []
        self._headers = [
            "ID", "Назва", "Вартість (UAH)", "Категорія", "Період", 
            "Остання оплата", "Наступна оплата", "Тип", "Стан"
        ]

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        subscription = self._data[index.row()]
        column = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            if column == 0:
                return str(subscription.id)
            elif column == 1:
                return subscription.name
            elif column == 2:
                return f"{subscription.cost_uah:.2f}"
            elif column == 3:
                return subscription.category.name if subscription.category else "N/A"
            elif column == 4:
                return subscription.period
            elif column == 5:
                return subscription.last_payment.strftime("%d.%m.%Y")
            elif column == 6:
                return subscription.next_payment.strftime("%d.%m.%Y")
            elif column == 7:
                return self._payment_type_map.get(subscription.payment_type, subscription.payment_type.value)
            elif column == 8:
                return self._state_map.get(subscription.state, subscription.state.value)
        
        elif role == Qt.ItemDataRole.BackgroundRole:
            if subscription.is_reminder_sent and subscription.state != SubscriptionState.OVERDUE:
                return QBrush(QColor("#FF4444")) # Красный цвет для напоминаний
            elif subscription.state == SubscriptionState.OVERDUE:
                return QBrush(QColor("#CC0000")) # Темно-красный для просроченных
        
        elif role == Qt.ItemDataRole.ForegroundRole:
            if (subscription.is_reminder_sent and subscription.state != SubscriptionState.OVERDUE) or \
               subscription.state == SubscriptionState.OVERDUE:
                return QBrush(QColor(Qt.GlobalColor.white))
            return QBrush(QColor(Qt.GlobalColor.white))

        elif role == Qt.ItemDataRole.UserRole:
            if column == 0:
                return subscription.id
            elif column == 1:
                return subscription.name
            elif column == 2:
                return subscription.cost_uah
            elif column == 3:
                return subscription.category.name if subscription.category else ""
            elif column == 4:
                return subscription.period
            elif column == 5:
                return datetime.combine(subscription.last_payment, datetime.min.time())
            elif column == 6:
                return datetime.combine(subscription.next_payment, datetime.min.time())
            elif column == 7:
                return subscription.payment_type.value
            elif column == 8:
                return subscription.state.value

        return None

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return None

    def get_subscription(self, row: int) -> Subscription:
        if 0 <= row < len(self._data):
            return self._data[row]
        return None

    def refresh_data(self, new_data: List[Subscription]):
        """Оновлює дані моделі та сповіщає view."""
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()
