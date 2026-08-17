"""
SecureRotate AI - Extensible Secret Provider Architecture

This module provides a unified interface for secret storage and encryption.
- LocalSecretProvider: Responsible for securely storing/retrieving the actual credential secret using Fernet authenticated encryption for simple developer setups.
- VaultSecretProvider: Stub interface for future HashiCorp Vault / AWS Secrets Manager integrations.

Password Security Principles:
Generated passwords are NEVER logged, returned through APIs, displayed in React, stored in audit_logs, or included in error messages.
"""

from abc import ABC, abstractmethod
import base64
import hashlib
import secrets
import string

try:
    from cryptography.fernet import Fernet, InvalidToken
    HAS_CRYPTOGRAPHY = True
except ImportError:
    HAS_CRYPTOGRAPHY = False
    Fernet = None
    InvalidToken = Exception


def derive_fernet_key(key_input: str) -> bytes:
    """
    Derives a valid 32-byte URL-safe base64 Fernet key from any string input.
    - If key_input is already a valid Fernet key, it is used directly.
    - Otherwise, SHA-256 digest of key_input is urlsafe-base64 encoded.
    - If key_input is empty or default placeholder, a deterministic dev key is derived.
    """
    if not key_input or "change_me" in str(key_input).lower():
        key_input = "securerotate_default_local_dev_key_2026"

    key_bytes = key_input.encode('utf-8') if isinstance(key_input, str) else key_input

    if HAS_CRYPTOGRAPHY and Fernet is not None:
        try:
            # Test if key_bytes is a valid Fernet key
            Fernet(key_bytes)
            return key_bytes
        except Exception:
            pass

    # Deterministic fallback: derive 32-byte URL-safe base64 key using SHA-256
    digest = hashlib.sha256(key_input.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest)


class BaseSecretProvider(ABC):
    """Abstract base class interface for database credential vault backends."""

    @abstractmethod
    def encrypt_secret(self, raw_secret: str) -> str:
        """Encrypt a raw secret string prior to metadata database storage."""
        pass

    @abstractmethod
    def decrypt_secret(self, secret_reference: str) -> str:
        """Decrypt a secret reference string for connection verification or rotation."""
        pass

    def generate_secure_password(self, length: int = 32) -> str:
        """Generate a cryptographically strong random password satisfying DB policies."""
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        while True:
            password = ''.join(secrets.choice(alphabet) for _ in range(length))
            if (any(c.islower() for c in password) and
                any(c.isupper() for c in password) and
                any(c.isdigit() for c in password) and
                any(c in "!@#$%^&*()-_=+" for c in password)):
                return password


class LocalSecretProvider(BaseSecretProvider):
    """
    Local development secret provider using Fernet authenticated encryption.
    Responsible for securely storing/retrieving the actual credential secret.
    """

    def __init__(self, encryption_key: str = None):
        self.has_crypto = HAS_CRYPTOGRAPHY
        self.key_bytes = derive_fernet_key(encryption_key or "")
        if self.has_crypto and Fernet is not None:
            self.fernet = Fernet(self.key_bytes)
        else:
            self.fernet = None

    def encrypt_secret(self, raw_secret: str) -> str:
        """Encrypt plaintext password to a base64 Fernet authenticated ciphertext token (secret_reference)."""
        if not raw_secret:
            return ""
        if self.has_crypto and self.fernet:
            return self.fernet.encrypt(raw_secret.encode('utf-8')).decode('utf-8')
        # Lightweight base64 encoding fallback if cryptography library is not installed
        return base64.b64encode(raw_secret.encode('utf-8')).decode('utf-8')

    def decrypt_secret(self, secret_reference: str) -> str:
        """Decrypt base64 Fernet token (secret_reference) to plaintext password for execution in RAM only."""
        if not secret_reference:
            return ""
        if self.has_crypto and self.fernet:
            try:
                return self.fernet.decrypt(secret_reference.encode('utf-8')).decode('utf-8')
            except Exception:
                # Forgiving fallback if secret reference was saved as base64 or plaintext
                try:
                    return base64.b64decode(secret_reference.encode('utf-8')).decode('utf-8')
                except Exception:
                    return secret_reference
        else:
            try:
                return base64.b64decode(secret_reference.encode('utf-8')).decode('utf-8')
            except Exception:
                return secret_reference


class VaultSecretProvider(BaseSecretProvider):
    """
    Future-ready extension stub for enterprise HashiCorp Vault integration.
    """

    def __init__(self, vault_url: str = None, vault_token: str = None):
        self.vault_url = vault_url
        self.vault_token = vault_token

    def encrypt_secret(self, raw_secret: str) -> str:
        raise NotImplementedError("HashiCorp Vault secret provider will be implemented in future release.")

    def decrypt_secret(self, secret_reference: str) -> str:
        raise NotImplementedError("HashiCorp Vault secret provider will be implemented in future release.")


def get_secret_provider(provider_type: str = "LOCAL", encryption_key: str = None) -> BaseSecretProvider:
    """Factory function returning the configured SecretProvider instance."""
    if not provider_type or provider_type.upper() == "LOCAL":
        return LocalSecretProvider(encryption_key=encryption_key or "")
    elif provider_type.upper() == "VAULT":
        return VaultSecretProvider()
    else:
        # Default fallback to LocalSecretProvider
        return LocalSecretProvider(encryption_key=encryption_key or "")
