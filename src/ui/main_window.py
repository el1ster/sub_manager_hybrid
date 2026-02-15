from PySide6.QtWidgets import QMainWindow, QTabWidget, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import QThread
from src.ui.styles import MAIN_STYLE
from src.ui.tabs.management_tab import ManagementTab
from src.core.currency_updater import update_currency_rates

class CurrencyUpdaterThread(QThread):
    """Потік для фонового оновлення курсів валют."""
    def run(self):
        update_currency_rates()

class MainWindow(QMainWindow):
    """Головне вікно додатка Hybrid Subscription Manager."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Hybrid Subscription Manager")
        self.resize(1200, 800) # Increased size for better layout
        
        # Основний віджет та лейаут
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Створення вкладок
        self.tabs = QTabWidget()
        self.setup_tabs()
        
        self.layout.addWidget(self.tabs)
        
        # Пристосування стилів
        self.setStyleSheet(MAIN_STYLE)

        # Запуск фонового оновлення курсів
        self.currency_updater = CurrencyUpdaterThread()
        self.currency_updater.start()

    def setup_tabs(self):
        """Ініціалізація вкладок відповідно до GEMINI.md."""
        # --- Вкладка Управління ---
        self.tab_management = ManagementTab()
        
        # --- Інші вкладки (поки заглушки) ---
        self.tab_stats = QWidget()
        self.tab_history = QWidget()
        self.tab_settings = QWidget()
        
        self.tabs.addTab(self.tab_management, "Управління")
        self.tabs.addTab(self.tab_stats, "Статистика")
        self.tabs.addTab(self.tab_history, "Історія")
        self.tabs.addTab(self.tab_settings, "Налаштування")
        
        # Тимчасові заглушки
        self.create_placeholder(self.tab_stats, "Тут будуть графіки витрат (PyQtGraph).")
        self.create_placeholder(self.tab_history, "Тут буде історія підтверджених платежів.")
        self.create_placeholder(self.tab_settings, "Налаштування безпеки, валют та бота.")

    def create_placeholder(self, tab, text):
        layout = QVBoxLayout(tab)
        label = QLabel(text)
        layout.addWidget(label)
