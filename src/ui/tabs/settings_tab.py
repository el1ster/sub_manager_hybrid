import random
import string
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QLabel, 
                               QPushButton, QHBoxLayout, QMessageBox, QApplication)
from PySide6.QtCore import Qt, QTimer, Signal
from src.database.db_manager import db
from src.core.models import SystemSettings

class SettingsTab(QWidget):
    """Вкладка налаштувань та спарювання з Telegram-ботом."""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
        self.check_pairing_status()

        # Timer to refresh status periodically
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_pairing_status)
        self.timer.start(5000) # Check every 5 seconds

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # --- Група "Telegram Bot" ---
        bot_group = QGroupBox("Інтеграція з Telegram")
        bot_layout = QVBoxLayout(bot_group)
        
        # Статус
        self.status_label = QLabel("Статус: ❌ Не підключено")
        self.status_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        
        # Контейнер для коду
        code_layout = QVBoxLayout()
        
        self.code_label = QLabel("-")
        self.code_label.setStyleSheet("""
            QLabel {
                font-size: 24px; 
                font-weight: bold; 
                color: #2E7D32; 
                background-color: #E8F5E9; 
                padding: 10px; 
                border-radius: 5px;
                border: 1px solid #C8E6C9;
            }
        """)
        self.code_label.setAlignment(Qt.AlignCenter)
        self.code_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.code_label.setVisible(False)
        
        self.copy_btn = QPushButton("📋 Копіювати команду")
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.clicked.connect(self.copy_code_to_clipboard)
        self.copy_btn.setVisible(False)
        
        code_layout.addWidget(self.code_label)
        code_layout.addWidget(self.copy_btn, alignment=Qt.AlignCenter)

        # Кнопки управління
        self.generate_btn = QPushButton("🔗 Згенерувати код підключення")
        self.generate_btn.setMinimumHeight(40)
        self.generate_btn.clicked.connect(self.generate_pairing_code)
        
        self.unlink_btn = QPushButton("❌ Відв'язати бота")
        self.unlink_btn.setStyleSheet("background-color: #FFEBEE; color: #C62828; border: 1px solid #FFCDD2;")
        self.unlink_btn.setMinimumHeight(40)
        self.unlink_btn.clicked.connect(self.unlink_bot)
        self.unlink_btn.setVisible(False)

        bot_layout.addWidget(self.status_label)
        bot_layout.addLayout(code_layout)
        bot_layout.addSpacing(10)
        bot_layout.addWidget(self.generate_btn)
        bot_layout.addWidget(self.unlink_btn)
        
        layout.addWidget(bot_group)
        layout.addStretch()

    def generate_pairing_code(self):
        """Generates a 6-digit code and saves it to DB."""
        code = ''.join(random.choices(string.digits, k=6))
        
        with db.get_session() as session:
            setting = session.query(SystemSettings).filter_by(setting_key="pairing_code").first()
            if not setting:
                session.add(SystemSettings(setting_key="pairing_code", setting_value=code))
            else:
                setting.setting_value = code
            session.commit()
            
        self.current_code = code
        self.code_label.setText(f"/pair {code}")
        self.code_label.setVisible(True)
        self.copy_btn.setVisible(True)
        self.generate_btn.setText("🔄 Згенерувати новий код")

    def copy_code_to_clipboard(self):
        """Copies the pair command to clipboard."""
        if hasattr(self, 'current_code'):
            cmd = f"/pair {self.current_code}"
            QApplication.clipboard().setText(cmd)
            self.copy_btn.setText("✅ Скопійовано!")
            QTimer.singleShot(2000, lambda: self.copy_btn.setText("📋 Копіювати команду"))

    def check_pairing_status(self):
        """Checks if a chat_id is linked."""
        with db.get_session() as session:
            linked_chat = session.query(SystemSettings).filter_by(setting_key="linked_chat_id").first()
            
            if linked_chat and linked_chat.setting_value:
                self.status_label.setText(f"Статус: ✅ Підключено (Chat ID: {linked_chat.setting_value})")
                self.code_label.setVisible(False)
                self.copy_btn.setVisible(False)
                self.generate_btn.setVisible(False)
                self.unlink_btn.setVisible(True)
            else:
                self.status_label.setText("Статус: ❌ Не підключено")
                self.unlink_btn.setVisible(False)
                self.generate_btn.setVisible(True)

    def unlink_bot(self):
        reply = QMessageBox.question(self, "Відв'язати бота", 
                                     "Ви впевнені? Бот більше не зможе надсилати заявки.",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            with db.get_session() as session:
                session.query(SystemSettings).filter_by(setting_key="linked_chat_id").delete()
                session.commit()
            
            self.check_pairing_status()
            self.generate_btn.setText("🔗 Згенерувати код підключення")

