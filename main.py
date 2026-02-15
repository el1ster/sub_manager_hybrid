import sys
from PySide6.QtWidgets import QApplication
from src.database.db_manager import db
from src.core.config import Config
from src.core.models import SystemSettings
from src.ui.main_window import MainWindow

def initialize_app():
    """Ініціалізація всіх систем додатка."""
    print("=== Hybrid Subscription Manager: Initializing Systems ===")
    
    # 1. Валідація конфігурації
    Config.validate()
    print(f"[*] Database location: {Config.DB_PATH}")
    
    # 2. Перевірка БД та безпеки
    try:
        session = db.get_session()
        enc_key = session.query(SystemSettings).filter_by(setting_key="enc_key").first()
        
        if enc_key:
            print("[+] Security System: AES-256 Key is active.")
        else:
            print("[!] Security System: Error retrieving encryption key.")
            
        session.close()
    except Exception as e:
        print(f"[!] Database Error: {e}")
        sys.exit(1)
        
    print("[+] All systems ready.")
    print("========================================================")

def main():
    # Початкова ініціалізація систем
    initialize_app()
    
    # Запуск GUI
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()