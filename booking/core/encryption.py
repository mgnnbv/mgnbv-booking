from cryptography.fernet import Fernet

from booking.core.config import settings


_fernet = Fernet(settings.encryption_key.encode())


def encrypt_text(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()


def decrypt_text(token: str) -> str:
    return _fernet.decrypt(token.encode()).decode()
