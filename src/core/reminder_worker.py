import time
from datetime import date, timedelta
from PySide6.QtCore import QThread
from src.database.db_manager import db
from src.core.models import Subscription, SystemSettings

class ReminderWorker(QThread):
    """
    Фоновий процес для перевірки наближення термінів оплати підписок
    та надсилання нагадувань через SyncQueue.
    """

    def __init__(self, days_before=3, check_interval_hours=4):
        super().__init__()
        self.running = True
        self.days_before = days_before
        self.check_interval_sec = check_interval_hours * 3600

    def run(self):
        print("[ReminderWorker] Starting up...")
        while self.running:
            try:
                self.check_for_upcoming_payments()
            except Exception as e:
                print(f"[ReminderWorker Error] {e}")
            
            # Wait for the next check
            self.sleep(self.check_interval_sec)

    def stop(self):
        print("[ReminderWorker] Shutting down...")
        self.running = False
        self.wait()

    def check_for_upcoming_payments(self):
        """Finds subscriptions that need payment soon and queues a reminder."""
        with db.get_session() as session:
            # 1. Get linked chat_id. If not linked, do nothing.
            linked_chat_setting = session.query(SystemSettings).filter_by(setting_key="linked_chat_id").first()
            if not (linked_chat_setting and linked_chat_setting.setting_value):
                # print("[ReminderWorker] System not paired. Skipping check.")
                return

            chat_id = int(linked_chat_setting.setting_value)
            
            # 2. Find upcoming subscriptions
            today = date.today()
            reminder_date_limit = today + timedelta(days=self.days_before)
            
            upcoming_subs = session.query(Subscription).filter(
                Subscription.next_payment >= today,
                Subscription.next_payment <= reminder_date_limit
            ).all()

            if not upcoming_subs:
                return

            print(f"[ReminderWorker] Found {len(upcoming_subs)} upcoming payments.")

            for sub in upcoming_subs:
                if not sub.is_reminder_sent: # Send reminder only if not already sent
                    # 3. Create a sync event for each reminder
                    db.add_sync_event("payment_reminder", {
                        "chat_id": chat_id,
                        "name": sub.name,
                        "cost_uah": sub.cost_uah,
                        "next_payment": sub.next_payment.strftime("%d.%m.%Y")
                    })
                    
                    # Mark reminder as sent
                    with db.get_session() as s:
                        s.query(Subscription).filter_by(id=sub.id).update({"is_reminder_sent": True})
                        s.commit()

        print("[ReminderWorker] Check complete.")
