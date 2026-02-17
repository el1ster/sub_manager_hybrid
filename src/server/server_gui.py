import sys
import os
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QPushButton, QTextEdit, QLabel, QLineEdit, QMessageBox)
from PySide6.QtCore import QProcess, Qt, QSettings
from PySide6.QtGui import QIcon

class ServerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("SubManager Hybrid Server")
        self.resize(600, 400)
        
        self.process = None
        self.settings = QSettings("SubManager", "ServerLauncher")
        
        # UI Components
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        
        # Token Input
        self.token_layout = QHBoxLayout()
        self.token_label = QLabel("Telegram Bot Token:")
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Enter token from @BotFather")
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        # Load saved token
        saved_token = self.settings.value("bot_token", "")
        self.token_input.setText(str(saved_token))
        
        # Toggle visibility button
        self.toggle_token_btn = QPushButton("👁")
        self.toggle_token_btn.setFixedWidth(30)
        self.toggle_token_btn.clicked.connect(self.toggle_token_visibility)
        
        self.token_layout.addWidget(self.token_label)
        self.token_layout.addWidget(self.token_input)
        self.token_layout.addWidget(self.toggle_token_btn)
        
        # Buttons
        self.btn_layout = QHBoxLayout()
        self.start_btn = QPushButton("Запустити сервер")
        self.stop_btn = QPushButton("Зупинити сервер")
        self.stop_btn.setEnabled(False)
        
        # Styling buttons
        self.start_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 8px;")
        self.stop_btn.setStyleSheet("background-color: #f44336; color: white; padding: 8px;")
        
        self.btn_layout.addWidget(self.start_btn)
        self.btn_layout.addWidget(self.stop_btn)
        
        # Log Area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: Consolas;")
        
        # Add to layout
        self.layout.addLayout(self.token_layout)
        self.layout.addLayout(self.btn_layout)
        self.layout.addWidget(QLabel("Server Logs:"))
        self.layout.addWidget(self.log_area)
        
        # Signals
        self.start_btn.clicked.connect(self.start_server)
        self.stop_btn.clicked.connect(self.stop_server)

    def log(self, message):
        self.log_area.append(message)

    def toggle_token_visibility(self):
        if self.token_input.echoMode() == QLineEdit.EchoMode.Password:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.toggle_token_btn.setStyleSheet("background-color: #ddd;") # Visual feedback
        else:
            self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.toggle_token_btn.setStyleSheet("")

    def start_server(self):
        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "Error", "Token is required!")
            return
            
        # Save token
        self.settings.setValue("bot_token", token)
            
        self.process = QProcess()
        self.process.setProgram(sys.executable)
        
        # Path to bot script
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bot", "main_bot.py"))
        self.process.setArguments([script_path])
        
        # Pass token via Environment Variable (Secure way)
        env = QProcess.systemEnvironment()
        env.append(f"BOT_TOKEN={token}")
        # Pass DB path explicitly to ensure bot finds it correctly
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "sub_manager.sqlite"))
        env.append(f"DB_PATH={db_path}")
        
        self.process.setEnvironment(env)
        
        # Handle Output
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.on_process_finished)
        
        self.process.start()
        
        self.log(f"[*] Starting bot process: {script_path}")
        self.log(f"[*] Database path: {db_path}")
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.token_input.setEnabled(False)

    def stop_server(self):
        if self.process:
            self.log("[*] Stopping server...")
            self.process.kill() # Use kill() for forceful and reliable termination

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        stdout = bytes(data).decode("utf-8")
        self.log(stdout.strip())

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        stderr = bytes(data).decode("utf-8")
        self.log(f"[ERROR] {stderr.strip()}")

    def on_process_finished(self):
        self.log("[!] Server stopped.")
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.token_input.setEnabled(True)
        self.process = None

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ServerWindow()
    window.show()
    sys.exit(app.exec())
