from datetime import datetime
from dateutil.relativedelta import relativedelta
from collections import defaultdict
from src.database.db_manager import db
from src.core.models import Subscription, SubscriptionState

class AnalyticsService:
    def get_expenses_by_category(self):
        """
        Повертає словник {category_name: total_uah} для активних підписок.
        """
        subscriptions = db.get_all_subscriptions()
        data = defaultdict(float)
        
        for sub in subscriptions:
            if sub.state == SubscriptionState.ACTIVE and sub.category:
                data[sub.category.name] += sub.cost_uah
                
        return dict(data)

    def get_monthly_forecast(self, months=12):
        """
        Розраховує прогноз витрат на N місяців вперед.
        Повертає список кортежів [(date_obj, total_uah), ...].
        """
        subscriptions = db.get_all_subscriptions()
        active_subs = [s for s in subscriptions if s.state == SubscriptionState.ACTIVE]
        
        start_date = datetime.now().date().replace(day=1)
        forecast = defaultdict(float)
        
        for i in range(months):
            current_month = start_date + relativedelta(months=i)
            month_key = current_month.strftime("%Y-%m") # Ключ для агрегації
            
            for sub in active_subs:
                # Визначаємо, чи платимо ми за цю підписку в цьому місяці
                should_pay = False
                
                # Логіка для різних періодів
                # Простий підхід: моделюємо платежі від next_payment
                
                # Знаходимо найближчу дату платежу в майбутньому (або сьогодні)
                payment_date = sub.next_payment
                
                # Якщо next_payment в минулому, "підтягуємо" його до актуального циклу
                # (в реальності це має оновлюватися, але для прогнозу моделюємо)
                while payment_date < start_date:
                    if sub.period == "Місяць": payment_date += relativedelta(months=1)
                    elif sub.period == "Квартал": payment_date += relativedelta(months=3)
                    elif sub.period == "Рік": payment_date += relativedelta(years=1)
                
                # Перевіряємо, чи потрапляє платіж у поточний місяць циклу
                # Ми перевіряємо 12 місяців. Для кожного місяця циклу (i) перевіряємо, чи є платіж
                # Простий алгоритм: генеруємо всі платежі підписки на рік вперед і сумуємо їх по місяцях
                
                # Оптимізований підхід:
                # Генеруємо дати платежів для цієї підписки на період прогнозу
                temp_date = payment_date
                while temp_date < start_date + relativedelta(months=months):
                    if temp_date.strftime("%Y-%m") == month_key:
                        forecast[month_key] += sub.cost_uah
                    
                    # Крок
                    if sub.period == "Місяць": temp_date += relativedelta(months=1)
                    elif sub.period == "Квартал": temp_date += relativedelta(months=3)
                    elif sub.period == "Рік": temp_date += relativedelta(years=1)

        # Формуємо відсортований список результатів
        result = []
        for i in range(months):
            date = start_date + relativedelta(months=i)
            key = date.strftime("%Y-%m")
            result.append((date, forecast[key]))
            
        return result

analytics = AnalyticsService()
