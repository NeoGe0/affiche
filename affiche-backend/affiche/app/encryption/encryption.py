from typing import Callable

from cryptography.fernet import Fernet
from sqlalchemy import String, TypeDecorator

class EncryptedString(TypeDecorator):
    impl = String
    cache_ok = True

    def __init__(self, key_provider: Callable[[], bytes], *args, **kwargs):
        self._key_provider = key_provider
        self._cipher = None
        super().__init__(*args, **kwargs)

    @property
    def cipher(self) -> Fernet:
        if self._cipher is None:
            self._cipher = Fernet(self._key_provider())
        return self._cipher

    def process_bind_param(self, value, dialect):
        if value is not None:
            return self.cipher.encrypt(value.encode()).decode()
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return self.cipher.decrypt(value.encode()).decode()
        return value
