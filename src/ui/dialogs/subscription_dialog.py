from PySide6.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit, 
                               QDoubleSpinBox, QComboBox, QDateEdit, QPushButton, 
                               QMessageBox, QLabel)
from PySide6.QtCore import QDate, Signal
from src.core.models import Subscription, Category, PaymentType, SubscriptionState
from src.database.db_manager import db
from typing import Optional
from dateutil.relativedelta import relativedelta

class SubscriptionDialog(QDialog):
    """Діалогове вікно для додавання або редагування підписки."""

    def __init__(self, subscription: Optional[Subscription] = None, is_draft_approval: bool = False):
        super().__init__()
        
        self.subscription = subscription
        self.is_edit_mode = self.subscription is not None

        title = "Редагувати підписку"
        if is_draft_approval:
            title = "Підтвердження чернетки"
        elif not self.is_edit_mode:
            title = "Додати підписку"
        self.setWindowTitle(title)
        
        # --- Створення віджетів ---
        self.name_edit = QLineEdit()
        self.cost_edit = QDoubleSpinBox()
        self.cost_edit.setRange(0.0, 99999.99)
        self.cost_edit.setSuffix(" UAH")
        self.category_combo = QComboBox()
        self.last_payment_edit = QDateEdit(QDate.currentDate())
        self.last_payment_edit.setCalendarPopup(True)
        self.period_combo = QComboBox()
        self.period_combo.addItems(["Місяць", "Квартал", "Рік"])
        self.next_payment_label = QLabel() # Для візуального предпросмотра
        self.payment_type_combo = QComboBox()
        self.payment_type_combo.addItems([e.value for e in PaymentType])
        
        self.ok_button = QPushButton("Зберегти" if self.is_edit_mode else "Додати")
        self.cancel_button = QPushButton("Скасувати")
        
        # --- Заповнення категорій ---
        self.categories = db.get_all_categories()
        for category in self.categories:
            self.category_combo.addItem(category.name, category.id)
            
        # --- Заповнення полів, якщо є дані ---
        if self.is_edit_mode:
            self.populate_fields()

        # --- Лейаут ---
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        form_layout.addRow("Назва:", self.name_edit)
        form_layout.addRow("Вартість:", self.cost_edit)
        form_layout.addRow("Категорія:", self.category_combo)
        form_layout.addRow("Дата останньої/першої оплати:", self.last_payment_edit)
        form_layout.addRow("Період підписки:", self.period_combo)
        form_layout.addRow("Дата наступної оплати:", self.next_payment_label)
        form_layout.addRow("Тип оплати:", self.payment_type_combo)
        
        layout.addLayout(form_layout)
        layout.addWidget(self.ok_button)
        layout.addWidget(self.cancel_button)
        
        # --- Сигнали ---
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        self.last_payment_edit.dateChanged.connect(self.update_next_payment_date)
        self.period_combo.currentIndexChanged.connect(self.update_next_payment_date)
        
        # --- Ініціалізація розрахунку ---
        self.update_next_payment_date()

    def populate_fields(self):
        """Заповнює поля даними з self.subscription."""
        self.name_edit.setText(self.subscription.name)
        self.cost_edit.setValue(self.subscription.cost_uah)
        
        if hasattr(self.subscription, 'last_payment') and self.subscription.last_payment:
            self.last_payment_edit.setDate(QDate(self.subscription.last_payment))

        self.period_combo.setCurrentText(self.subscription.period)
        self.payment_type_combo.setCurrentText(self.subscription.payment_type.value)
        
        cat_index = self.category_combo.findData(self.subscription.category_id)
        if cat_index != -1:
            self.category_combo.setCurrentIndex(cat_index)

    def update_next_payment_date(self):
        """Реактивно розраховує та оновлює дату наступного платежу."""
        last_date = self.last_payment_edit.date().toPython()
        period = self.period_combo.currentText()
        
        delta = None
        if period == "Місяць":
            delta = relativedelta(months=1)
        elif period == "Квартал":
            delta = relativedelta(months=3)
        elif period == "Рік":
            delta = relativedelta(years=1)
        
        if delta:
            next_date = last_date + delta
            self.next_payment_label.setText(next_date.strftime("%Y-%m-%d"))

    def get_data(self) -> Optional[Subscription]:
        """Повертає зібрані дані у вигляді об'єкта Subscription."""
        if not self.name_edit.text().strip():
            QMessageBox.warning(self, "Помилка валідації", "Назва не може бути порожньою.")
            return None

        # Створюємо новий об'єкт або використовуємо існуючий
        sub = self.subscription if self.is_edit_mode else Subscription()
        if not self.is_edit_mode:
            sub.state = SubscriptionState.ACTIVE 

        sub.name = self.name_edit.text().strip()
        sub.cost_uah = self.cost_edit.value()
        sub.category_id = self.category_combo.currentData()
        sub.period = self.period_combo.currentText()
        sub.last_payment = self.last_payment_edit.date().toPython()
        sub.payment_type = PaymentType(self.payment_type_combo.currentText())
        
        # Розрахунок next_payment перед збереженням
        delta = None
        if sub.period == "Місяць":
            delta = relativedelta(months=1)
        elif sub.period == "Квартал":
            delta = relativedelta(months=3)
        elif sub.period == "Рік":
            delta = relativedelta(years=1)
        if delta:
            sub.next_payment = sub.last_payment + delta
        else:
             sub.next_payment = sub.last_payment # Fallback

        return sub
