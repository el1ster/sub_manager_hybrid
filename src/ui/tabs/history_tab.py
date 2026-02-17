from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTableView, QHeaderView, 
                               QGroupBox, QLineEdit)
from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex, QSortFilterProxyModel
from typing import List, Any
from src.core.models import PaymentHistory, Subscription
from src.database.db_manager import db
from datetime import datetime

class PaymentHistoryModel(QAbstractTableModel):
    """Модель для відображення історії платежів у QTableView."""

    def __init__(self, data: List[PaymentHistory] = None):
        super().__init__()
        self._data = data or []
        self._headers = ["ID", "Назва підписки", "Сума (UAH)", "Дата оплати"]

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None

        history_item = self._data[index.row()]
        column = index.column()
            
        if role == Qt.ItemDataRole.DisplayRole:
            if column == 0:
                return str(history_item.id)
            elif column == 1:
                return history_item.subscription.name if history_item.subscription else "N/A"
            elif column == 2:
                return f"{history_item.final_sum:.2f}"
            elif column == 3:
                return history_item.pay_date.strftime("%d.%m.%Y %H:%M")
        
        # UserRole for sorting removed as requested to revert to default behavior
        
        return None

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._data)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self._headers)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return self._headers[section]
        return None

    def refresh_data(self, new_data: List[PaymentHistory]):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

class HistoryFilterProxyModel(QSortFilterProxyModel):
    """Кастомний фільтр для пошуку по всіх колонках."""
    
    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        regex = self.filterRegularExpression()
        
        # Перевіряємо всі колонки
        for col in range(model.columnCount()):
            index = model.index(source_row, col, source_parent)
            data = model.data(index, Qt.ItemDataRole.DisplayRole)
            
            if data and regex.match(str(data)).hasMatch():
                return True
                
        return False

class HistoryTab(QWidget):
    """Віджет для вкладки 'Історія'."""

    def __init__(self):
        super().__init__()
        
        main_layout = QVBoxLayout(self)
        table_group = QGroupBox("Історія всіх підтверджених платежів")
        table_layout = QVBoxLayout(table_group)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Пошук в історії...")
        
        self.table_view = QTableView()
        self.table_model = PaymentHistoryModel()
        
        # Custom Proxy for filtering
        self.proxy_model = HistoryFilterProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        
        self.table_view.setModel(self.proxy_model)
        
        # Table view settings
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.setSortingEnabled(True) # Standard Qt sorting (DisplayRole)
        
        table_layout.addWidget(self.search_edit)
        table_layout.addWidget(self.table_view)
        main_layout.addWidget(table_group)
        
        self.search_edit.textChanged.connect(self.proxy_model.setFilterRegularExpression)
        
        self.load_history()

    def load_history(self):
        """Завантажує історію з БД та оновлює таблицю."""
        history = db.get_payment_history()
        self.table_model.refresh_data(history)

    def refresh_data(self):
        """Public method to be called when tab is switched."""
        self.load_history()
