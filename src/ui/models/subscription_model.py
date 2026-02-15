from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex
from typing import List, Any
from src.core.models import Subscription

class SubscriptionTableModel(QAbstractTableModel):
    """Модель для відображення підписок у QTableView."""

    def __init__(self, data: List[Subscription] = None):
        super().__init__()
        self._data = data or []
        self._headers = ["ID", "Назва", "Вартість (UAH)", "Категорія", "Наступний платіж", "Стан"]

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            subscription = self._data[index.row()]
            column = index.column()
            
            if column == 0:
                return str(subscription.id)
            elif column == 1:
                return subscription.name
            elif column == 2:
                return f"{subscription.cost_uah:.2f}"
            elif column == 3:
                return subscription.category.name if subscription.category else "N/A"
            elif column == 4:
                return subscription.next_payment.strftime("%Y-%m-%d")
            elif column == 5:
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

