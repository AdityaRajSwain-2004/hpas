"""AES-256 PII encryption using Fernet"""
from cryptography.fernet import Fernet
from app.core.settings import settings
from typing import Optional
import logging

log = logging.getLogger(__name__)

_fernet = None

def _get_fernet() -> Optional[Fernet]:
    global _fernet
    if _fernet is None and settings.ENCRYPTION_KEY:
        try:
            key = settings.ENCRYPTION_KEY
            if len(key) < 44:
                key = Fernet.generate_key().decode()
                log.warning("ENCRYPTION_KEY too short — using generated key (data won't persist across restarts)")
            _fernet = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            log.error("Failed to init Fernet: %s", e)
    return _fernet

def encrypt(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    f = _get_fernet()
    if not f:
        return value  # dev mode without encryption key
    try:
        return f.encrypt(value.encode()).decode()
    except Exception:
        return value

def decrypt(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    f = _get_fernet()
    if not f:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except Exception:
        return value  # may already be plaintext
