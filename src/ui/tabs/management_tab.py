import re
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableView, QPushButton,
                               QHeaderView, QAbstractItemView, QGroupBox, QListWidget, 
                               QListWidgetItem, QMessageBox, QLineEdit)
from PySide6.QtCore import Qt, QSortFilterProxyModel
from src.ui.models.subscription_model import SubscriptionTableModel
from src.ui.dialogs.subscription_dialog import SubscriptionDialog
from src.database.db_manager import db
from src.core.models import Subscription, Draft, PaymentType, PaymentHistory, SubscriptionState

class SubscriptionFilterProxyModel(QSortFilterProxyModel):
    """Кастомний фільтр для пошуку по всіх колонках, крім ID."""
    
    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        regex = self.filterRegularExpression()
        
        # Перевіряємо всі колонки, починаючи з 1 (пропускаємо ID)
        for col in range(1, model.columnCount()):
            index = model.index(source_row, col, source_parent)
            data = model.data(index, Qt.ItemDataRole.DisplayRole)
            
            if data and regex.match(str(data)).hasMatch():
                return True
                
        return False

class ManagementTab(QWidget):
    """Віджет для вкладки 'Управління'."""

    def __init__(self):
        super().__init__()
        
        # --- Основний лейаут ---
        main_layout = QHBoxLayout(self)
        
        # --- Ліва частина (Таблиця підписок) ---
        table_group = QGroupBox("Активні підписки")
        table_layout = QVBoxLayout(table_group)
        
        # Пошук підписок
        self.search_subs_edit = QLineEdit()
        self.search_subs_edit.setPlaceholderText("Пошук підписки...")
        
        self.table_view = QTableView()
        self.table_model = SubscriptionTableModel()
        
        # Proxy Model для фільтрації
        self.proxy_model = SubscriptionFilterProxyModel()
        self.proxy_model.setSourceModel(self.table_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        # self.proxy_model.setFilterKeyColumn(1) - Не потрібно, логіка в класі
        
        self.table_view.setModel(self.proxy_model)
        
        # Налаштування вигляду таблиці
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        self.add_button = QPushButton("Додати підписку")
        self.edit_button = QPushButton("Редагувати")
        self.delete_button = QPushButton("Видалити")
        self.mark_paid_button = QPushButton("Відзначити як сплачене")
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addWidget(self.add_button)
        buttons_layout.addWidget(self.edit_button)
        buttons_layout.addWidget(self.delete_button)
        buttons_layout.addWidget(self.mark_paid_button)
        
        table_layout.addWidget(self.search_subs_edit)
        table_layout.addWidget(self.table_view)
        table_layout.addLayout(buttons_layout)
        
        # --- Права частина (Панель чернеток) ---
        self.drafts_group = QGroupBox("Чернетки з Telegram")
        drafts_layout = QVBoxLayout(self.drafts_group)
        
        # Пошук чернеток
        self.search_drafts_edit = QLineEdit()
        self.search_drafts_edit.setPlaceholderText("Пошук чернетки...")
        
        self.drafts_list = QListWidget()
        self.approve_button = QPushButton("Створити підписку")
        self.reject_button = QPushButton("Відхилити")

        drafts_buttons_layout = QHBoxLayout()
        drafts_buttons_layout.addWidget(self.approve_button)
        drafts_buttons_layout.addWidget(self.reject_button)

        drafts_layout.addWidget(self.search_drafts_edit)
        drafts_layout.addWidget(self.drafts_list)
        drafts_layout.addLayout(drafts_buttons_layout)
        
        # --- Компонування ---
        main_layout.addWidget(table_group, 7) # 70% ширини
        main_layout.addWidget(self.drafts_group, 3) # 30% ширини
        
        # --- Сигнали ---
        self.add_button.clicked.connect(self.add_subscription)
        self.edit_button.clicked.connect(self.edit_subscription)
        self.delete_button.clicked.connect(self.delete_subscription)
        self.mark_paid_button.clicked.connect(self.mark_as_paid) # Connect new button
        self.approve_button.clicked.connect(self.approve_draft)
        self.reject_button.clicked.connect(self.reject_draft)
        
        self.search_subs_edit.textChanged.connect(self.proxy_model.setFilterRegularExpression)
        self.search_drafts_edit.textChanged.connect(self.filter_drafts)
        
        # --- Завантаження даних ---
        self.load_subscriptions()
        self.load_drafts()

    def refresh_all_data(self):
        """Оновлює всі дані на вкладці."""
        self.load_subscriptions()
        self.load_drafts()

    def load_subscriptions(self):
        """Завантажує підписки з БД та оновлює таблицю."""
        subscriptions = db.get_all_subscriptions()
        self.table_model.refresh_data(subscriptions)

    def load_drafts(self):
        """Завантажує чернетки та оновлює список."""
        self.drafts_list.clear()
        drafts = db.get_pending_drafts()
        
        self.drafts_group.setVisible(bool(drafts))
        
        for draft in drafts:
            item_text = f"{draft.raw_name} - {draft.amount} {draft.currency}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, draft.id)
            self.drafts_list.addItem(item)
            
    def filter_drafts(self, text):
        """Фільтрує список чернеток."""
        for i in range(self.drafts_list.count()):
            item = self.drafts_list.item(i)
            item.setHidden(text.lower() not in item.text().lower())

    def add_subscription(self):
        dialog = SubscriptionDialog()
        if dialog.exec():
            new_sub_data = dialog.get_data()
            if new_sub_data:
                db.add_subscription(new_sub_data)
                self.load_subscriptions()

    def edit_subscription(self):
        selected_rows = self.table_view.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Помилка", "Будь ласка, оберіть підписку для редагування.")
            return
        
        # Отримуємо індекс з proxy model
        proxy_index = selected_rows[0]
        # Конвертуємо в індекс source model
        source_index = self.proxy_model.mapToSource(proxy_index)
        row_index = source_index.row()
        
        subscription_to_edit = self.table_model.get_subscription(row_index)
        
        if subscription_to_edit:
            dialog = SubscriptionDialog(subscription=subscription_to_edit)
            if dialog.exec():
                updated_sub_data = dialog.get_data()
                if updated_sub_data:
                    # Словник для оновлення полів
                    update_dict = {
                        "name": updated_sub_data.name,
                        "cost_uah": updated_sub_data.cost_uah,
                        "category_id": updated_sub_data.category_id,
                        "period": updated_sub_data.period,
                        "last_payment": updated_sub_data.last_payment,
                        "next_payment": updated_sub_data.next_payment,
                        "payment_type": updated_sub_data.payment_type
                    }
                    db.update_subscription(subscription_to_edit.id, update_dict)
                    self.load_subscriptions()

    def delete_subscription(self):
        selected_rows = self.table_view.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Помилка", "Будь ласка, оберіть підписку для видалення.")
            return
            
        # Отримуємо індекс з proxy model
        proxy_index = selected_rows[0]
        # Конвертуємо в індекс source model
        source_index = self.proxy_model.mapToSource(proxy_index)
        row_index = source_index.row()
        
        subscription_to_delete = self.table_model.get_subscription(row_index)
        
        if subscription_to_delete:
            reply = QMessageBox.question(self, "Підтвердження",
                                         f"Ви впевнені, що хочете видалити '{subscription_to_delete.name}'?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                db.delete_subscription(subscription_to_delete.id)
                # Фідбек боту про видалення (без chat_id, так как подписка уже на ПК)
                db.add_sync_event("subscription_deleted", {"name": subscription_to_delete.name})
                self.load_subscriptions()
    
    def approve_draft(self):
        selected_item = self.drafts_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Помилка", "Будь ласка, оберіть чернетку для обробки.")
            return
            
        draft_id = selected_item.data(Qt.ItemDataRole.UserRole)
        draft = db.get_draft_by_id(draft_id)
        
        if draft:
            # 1. Очистка назви (Regex)
            clean_name = re.sub(r'^(Telegram|Заявка|Bot|Request)[:\s-]*', '', draft.raw_name, flags=re.IGNORECASE).strip()
            
            # 2. Конвертація валюти
            rate = db.get_currency_rate(draft.currency)
            cost_in_uah = round(draft.amount * rate, 2)

            # Створюємо тимчасовий об'єкт Subscription з обробленими даними
            temp_sub = Subscription(
                name=clean_name, 
                cost_uah=cost_in_uah,
                payment_type=PaymentType.AUTO, # Значення за замовчуванням
                period="Місяць"               # Значення за замовчуванням
            )
            
            dialog = SubscriptionDialog(subscription=temp_sub, is_draft_approval=True)
            if dialog.exec():
                new_sub = dialog.get_data()
                if new_sub:
                    sub_name = new_sub.name
                    sub_cost = new_sub.cost_uah
                    
                    chat_id = db.approve_draft(draft_id, new_sub)
                    
                    db.add_sync_event("subscription_approved", {
                        "original_draft": draft.raw_name,
                        "new_name": sub_name,
                        "cost_uah": sub_cost,
                        "chat_id": chat_id
                    })
                    self.refresh_all_data()

    def reject_draft(self):
        selected_item = self.drafts_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Помилка", "Будь ласка, оберіть чернетку для відхилення.")
            return

        draft_id = selected_item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, "Підтвердження",
                                     f"Ви впевнені, що хочете відхилити цю чернетку?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            chat_id = db.reject_draft(draft_id)
            db.add_sync_event("draft_rejected", {"draft_id": draft_id, "chat_id": chat_id})
            self.load_drafts()

    def mark_as_paid(self):
        selected_rows = self.table_view.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.warning(self, "Помилка", "Будь ласка, оберіть підписку для відзначення як сплаченої.")
            return
        
        proxy_index = selected_rows[0]
        source_index = self.proxy_model.mapToSource(proxy_index)
        row_index = source_index.row()
        
        subscription_to_mark = self.table_model.get_subscription(row_index)
        
        if subscription_to_mark:
            reply = QMessageBox.question(self, "Підтвердження платежу",
                                         f"Підтвердити оплату для '{subscription_to_mark.name}' (Сума: {subscription_to_mark.cost_uah:.2f} UAH)?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                from datetime import date
                from dateutil.relativedelta import relativedelta

                new_last_payment = date.today()
                
                delta = None
                if subscription_to_mark.period == "Місяць":
                    delta = relativedelta(months=1)
                elif subscription_to_mark.period == "Квартал":
                    delta = relativedelta(months=3)
                elif subscription_to_mark.period == "Рік":
                    delta = relativedelta(years=1)
                
                new_next_payment = new_last_payment + delta if delta else new_last_payment

                db.mark_subscription_paid(
                    subscription_to_mark.id, 
                    new_last_payment, 
                    new_next_payment, 
                    subscription_to_mark.cost_uah
                )
                QMessageBox.information(self, "Успіх", f"Підписка '{subscription_to_mark.name}' відзначена як сплачена.")
                self.refresh_all_data()
