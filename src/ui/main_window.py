import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import QThread
from src.ui.styles import DARK_THEME_QSS
from src.ui.tabs.management_tab import ManagementTab
from src.ui.tabs.stats_tab import StatsTab
from src.ui.tabs.settings_tab import SettingsTab
from src.ui.tabs.history_tab import HistoryTab
from src.core.currency_updater import update_currency_rates
from src.core.sync_worker import SyncWorker
from src.core.reminder_worker import ReminderWorker

class CurrencyUpdaterThread(QThread):
    """Потік для фонового оновлення курсів валют."""
    def run(self):
        update_currency_rates()

class MainWindow(QMainWindow):
    """Головне вікно додатка Hybrid Subscription Manager."""
    
    def __init__(self, app):
        super().__init__()
        self.app = app # Store app instance to apply styles globally
        
        self.setWindowTitle("Hybrid Subscription Manager")
        self.resize(1200, 800)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        self.tabs = QTabWidget()
        self.setup_tabs()
        
        self.layout.addWidget(self.tabs)
        
        # --- Застосування темної теми ---
        self.app.setStyleSheet(DARK_THEME_QSS)
        # Сразу обновим графики, так как тема жестко задана
        self.tab_stats.update_theme(is_dark=True)
        
        # --- Запуск фонових процесів ---
        self.currency_updater = CurrencyUpdaterThread()
        self.currency_updater.start()

        self.sync_worker = SyncWorker()
        self.sync_worker.draft_received.connect(self.on_draft_received)
        self.sync_worker.start()
        
        self.reminder_worker = ReminderWorker()
        self.reminder_worker.start()
        
        self.destroyed.connect(self.stop_workers)

    def setup_tabs(self):
        """Ініціалізація вкладок."""
        self.tab_management = ManagementTab()
        self.tab_stats = StatsTab()
        self.tab_settings = SettingsTab()
        self.tab_history = HistoryTab()
        
        self.tabs.addTab(self.tab_management, "Управління")
        self.tabs.addTab(self.tab_stats, "Статистика")
        self.tabs.addTab(self.tab_history, "Історія")
        self.tabs.addTab(self.tab_settings, "Налаштування")
        
        # Підключення сигналу зміни вкладки
        self.tabs.currentChanged.connect(self.on_tab_changed)

    def on_tab_changed(self, index):
        """Оновлює дані при перемиканні вкладок."""
        if index == 0: # Management
            self.tab_management.refresh_all_data()
        elif index == 1: # Stats
            self.tab_stats.refresh_stats()
        elif index == 2: # History
            self.tab_history.refresh_data()

    def on_draft_received(self):
        """Викликається, коли прийшла нова чернетка від бота."""
        self.tab_management.load_drafts()
        self.statusBar().showMessage("📩 Отримано нову заявку з Telegram!", 5000)

    def stop_workers(self):
        """Зупиняє всі фонові потоки."""
        print("Stopping background workers...")
        self.sync_worker.stop()
        self.reminder_worker.stop()
        print("Workers stopped.")