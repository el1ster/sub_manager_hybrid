import json
from cryptography.fernet import Fernet
from typing import Any, Dict

class SecurityManager:
    """Менеджер безпеки для шифрування даних (AES-256)."""

    def __init__(self, key: str):
        """
        Ініціалізація з ключем Fernet.
        :param key: Ключ у форматі string або bytes.
        """
        try:
            self.fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            raise ValueError(f"Невалідний ключ шифрування: {e}")

    def encrypt_data(self, data: Dict[str, Any]) -> str:
        """
        Шифрує словник (dict) у зашифрований рядок.
        :param data: Дані для шифрування.
        :return: Зашифрований рядок (token).
        """
        json_data = json.dumps(data).encode('utf-8')
        encrypted_token = self.fernet.encrypt(json_data)
        return encrypted_token.decode('utf-8')

    def decrypt_data(self, token: str) -> Dict[str, Any]:
        """
        Розшифровує рядок у словник (dict).
        :param token: Зашифрований рядок.
        :return: Розшифрований словник.
        """
        decrypted_data = self.fernet.decrypt(token.encode('utf-8'))
        return json.loads(decrypted_data.decode('utf-8'))

    @staticmethod
    def generate_new_key() -> str:
        """Генерує новий випадковий ключ AES-256 (Fernet)."""
        return Fernet.generate_key().decode('utf-8')
