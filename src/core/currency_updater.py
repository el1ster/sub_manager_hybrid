import requests
import logging
from src.database.db_manager import db
from src.core.models import Currency

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

NBU_API_URL = "https://bank.gov.ua/NBUStatService/v1/statdirectory/exchange?json"

def update_currency_rates():
    """
    Оновлює курси валют (USD, EUR) в базі даних, використовуючи API НБУ.
    Працює в режимі 'fail-safe': якщо API недоступний, використовуються старі значення.
    """
    try:
        logger.info("Спроба оновлення курсів валют через API НБУ...")
        response = requests.get(NBU_API_URL, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        rates = {item['cc']: item['rate'] for item in data}
        
        updated_count = 0
        with db.get_session() as session:
            # Отримуємо всі валюти, які не є базовими (не UAH)
            currencies = session.query(Currency).filter(Currency.is_base == False).all()
            
            for currency in currencies:
                if currency.code in rates:
                    new_rate = rates[currency.code]
                    if currency.manual_rate != new_rate:
                        currency.manual_rate = new_rate
                        updated_count += 1
                        logger.info(f"Оновлено курс {currency.code}: {new_rate}")
            
            if updated_count > 0:
                session.commit()
                logger.info(f"Успішно оновлено {updated_count} валют.")
            else:
                logger.info("Курси валют актуальні, оновлення не потрібне.")
                
    except requests.RequestException as e:
        logger.warning(f"Не вдалося оновити курси валют (API недоступний): {e}")
    except Exception as e:
        logger.error(f"Помилка при оновленні курсів: {e}")
