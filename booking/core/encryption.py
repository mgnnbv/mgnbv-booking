from cryptography.fernet import Fernet

from booking.core.config import settings

# Паспортные данные жильца — персональные данные по 152-ФЗ, поэтому хранятся
# в БД только в зашифрованном виде. Ключ живёт в переменной окружения, не в
# коде и не в БД.
_fernet = Fernet(settings.encryption_key.encode())


def encrypt_text(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def decrypt_text(token: str) -> str:
    return _fernet.decrypt(token.encode()).decode()
