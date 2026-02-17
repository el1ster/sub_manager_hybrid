import json
import time
import uuid
from PySide6.QtCore import QThread, Signal
from src.database.db_manager import db
from src.core.models import SyncQueue, SyncDirection, Draft, SystemSettings
from cryptography.fernet import Fernet

class SyncWorker(QThread):
    """Фоновий процес для синхронізації даних з ботом (через БД)."""
    
    draft_received = Signal() # Сигнал про отримання нової чернетки

    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True

    def run(self):
        while self.running:
            try:
                self.process_queue()
            except Exception as e:
                print(f"[SyncWorker Error] {e}")
            
            # Пауза перед наступною перевіркою
            time.sleep(3)

    def stop(self):
        self.running = False
        self.wait()

    def _add_feedback(self, session, event, data):
        """Helper to add feedback to SyncQueue within existing session."""
        payload_json = json.dumps({"event": event, "data": data}, ensure_ascii=False)

        enc_key_setting = session.query(SystemSettings).filter_by(setting_key="enc_key").first()
        if not enc_key_setting:
            print("[Security Error] Encryption key not found. Cannot encrypt sync event.")
            encrypted_payload = payload_json.encode('utf-8')
        else:
            fernet = Fernet(enc_key_setting.setting_value.encode('utf-8'))
            encrypted_payload = fernet.encrypt(payload_json.encode('utf-8'))

        sync_item = SyncQueue(
            uuid=str(uuid.uuid4()),
            payload=encrypted_payload.decode('utf-8'),
            direction=SyncDirection.TO_BOT
        )
        session.add(sync_item)

    def process_queue(self):
        with db.get_session() as session:
            # Шукаємо повідомлення ВІД бота
            messages = session.query(SyncQueue).filter_by(direction=SyncDirection.FROM_BOT).limit(5).all()
            
            if not messages:
                return

            new_drafts_count = 0
            
            # Отримати прив'язаний чат ID
            linked_chat_setting = session.query(SystemSettings).filter_by(setting_key="linked_chat_id").first()
            linked_chat_id = int(linked_chat_setting.setting_value) if linked_chat_setting else None
            
            for msg in messages:
                try:
                    # Decrypt payload
                    enc_key_setting = session.query(SystemSettings).filter_by(setting_key="enc_key").first()
                    if not enc_key_setting:
                        print("[Security Error] Encryption key not found. Cannot decrypt sync event.")
                        continue # Skip message if no key
                    
                    fernet = Fernet(enc_key_setting.setting_value.encode('utf-8'))
                    
                    try:
                        decrypted_payload = fernet.decrypt(msg.payload.encode('utf-8')).decode('utf-8')
                        data = json.loads(decrypted_payload)
                    except Exception as e:
                        print(f"[Security Error] Failed to decrypt or parse payload for msg {msg.uuid}: {e}")
                        session.delete(msg) # Remove problematic message
                        continue
                    
                    event_type = data.get("event") # e.g., "pairing_request" or None (for legacy drafts)
                    chat_id = data.get("chat_id")
                    
                    # --- Pairing Request ---
                    if event_type == "pairing_request":
                        code_input = data.get("code")
                        code_setting = session.query(SystemSettings).filter_by(setting_key="pairing_code").first()
                        
                        if code_setting and code_setting.setting_value == code_input:
                            # Успішне спарювання
                            if not linked_chat_setting:
                                linked_chat_setting = SystemSettings(setting_key="linked_chat_id", setting_value=str(chat_id))
                                session.add(linked_chat_setting)
                            else:
                                linked_chat_setting.setting_value = str(chat_id)
                                
                            # Очистити код після використання
                            session.delete(code_setting)
                            
                            # Фідбек боту
                            self._add_feedback(session, "pairing_success", {"chat_id": chat_id})
                        else:
                            # Невдале спарювання
                            self._add_feedback(session, "pairing_failed", {"chat_id": chat_id})
                            
                        session.delete(msg)
                        session.commit() # Commit immediately for pairing
                        continue

                    # --- Draft Processing ---
                    # Если система привязана, проверяем chat_id
                    if linked_chat_id and chat_id != linked_chat_id:
                        print(f"[Security] Ignored draft from unauthorized chat_id: {chat_id}")
                        session.delete(msg) # Silently drop unauthorized messages
                        continue
                        
                    # Если система НЕ привязана, игнорируем все чернетки (или дозволяем лишь pairing)
                    if not linked_chat_id:
                        print(f"[Security] System not paired. Ignoring draft from {chat_id}")
                        self._add_feedback(session, "error_not_paired", {"chat_id": chat_id})
                        session.delete(msg)
                        continue

                    # Создать чернетку (только если прошли проверки)
                    new_draft = Draft(
                        raw_name=data.get("raw_name", "Unknown"),
                        amount=float(data.get("amount", 0.0)),
                        currency=data.get("currency", "UAH"),
                        chat_id=data.get("chat_id")  # Save chat_id
                    )
                    session.add(new_draft)
                    session.flush() # Чтобы получить ID
                    
                    # Фідбек боту об отриманні (Присвоєння ID)
                    if new_draft.chat_id:
                        self._add_feedback(session, "draft_received", {
                            "draft_id": new_draft.id,
                            "chat_id": new_draft.chat_id,
                            "name": new_draft.raw_name
                        })
                    
                    # Видалити з черги (оброблено)
                    session.delete(msg)
                    new_drafts_count += 1
                    
                except Exception as e:
                    print(f"[SyncWorker] Failed to process msg {msg.uuid}: {e}")
            
            if new_drafts_count > 0:
                session.commit()
                self.draft_received.emit()
