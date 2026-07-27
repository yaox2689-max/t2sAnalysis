"""Credential encryption — encrypt/decrypt MySQL passwords for storage.

Uses Fernet symmetric encryption. The key is derived from JWT_SECRET_KEY.

Usage:
    from app.services.credential_encryption import encrypt_password, decrypt_password

    encrypted = encrypt_password("my_password")
    decrypted = decrypt_password(encrypted)
"""

from __future__ import annotations

import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet

from app.core.config import settings

_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    """Get or create Fernet instance from JWT_SECRET_KEY."""
    global _fernet
    if _fernet is None:
        key = hashlib.sha256(settings.JWT_SECRET_KEY.encode()).digest()
        _fernet = Fernet(base64.urlsafe_b64encode(key))
    return _fernet


def encrypt_password(plain: str) -> str:
    """Encrypt a password for storage."""
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_password(encrypted: str) -> str:
    """Decrypt a stored password."""
    return _get_fernet().decrypt(encrypted.encode()).decode()
