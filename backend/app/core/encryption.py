import base64
import hashlib
import json
import re
from typing import Any
from urllib.parse import urlparse

from cryptography.fernet import Fernet

from app.core.config import settings

SENSITIVE_FIELD_NAMES = {
    "password",
    "token",
    "access_token",
    "api_token",
    "api_key",
    "secret",
    "client_secret",
    "security_token",
    "private_key",
    "sasl_password",
}


def _get_fernet_key() -> bytes:
    """Derives a deterministic 32-byte Fernet key from secret_key setting."""
    raw_key = getattr(settings, "credential_encryption_key", None) or getattr(settings, "secret_key", "context-trust-master-encryption-secret-key-32b")
    # Hash to 32 bytes and base64 encode
    digest = hashlib.sha256(raw_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


class EncryptionService:
    """Provides envelope encryption at rest for connector credentials and secret redaction."""

    _fernet: Fernet | None = None

    @classmethod
    def get_cipher(cls) -> Fernet:
        if cls._fernet is None:
            cls._fernet = Fernet(_get_fernet_key())
        return cls._fernet

    @classmethod
    def encrypt_payload(cls, data: dict[str, Any]) -> str:
        """Serializes and encrypts dictionary payload into encrypted token string."""
        if not data:
            return ""
        cipher = cls.get_cipher()
        raw_json = json.dumps(data).encode("utf-8")
        return cipher.encrypt(raw_json).decode("utf-8")

    @classmethod
    def decrypt_payload(cls, token: str) -> dict[str, Any]:
        """Decrypts encrypted token string back to dictionary payload."""
        if not token:
            return {}
        try:
            cipher = cls.get_cipher()
            decrypted = cipher.decrypt(token.encode("utf-8"))
            return json.loads(decrypted.decode("utf-8"))
        except Exception:
            return {}

    @classmethod
    def mask_uri(cls, uri: str) -> str:
        """Masks username and password embedded in connection URIs."""
        if not uri:
            return ""
        try:
            # Mask user:pass@host
            return re.sub(r"(://)([^:@\s]+):([^@\s]+)@", r"\1\2:••••••••@", uri)
        except Exception:
            return "mongodb://••••••••@***"

    @classmethod
    def redact_credentials(cls, config: dict[str, Any] | None) -> dict[str, Any]:
        """Creates a safe copy of configuration with all credentials redacted."""
        if not config:
            return {}
        safe_copy = {}
        for key, value in config.items():
            k_lower = key.lower()
            if k_lower in ("encrypted_credentials", "_encrypted_credentials"):
                continue  # Never expose encrypted payload directly
            if any(sensitive in k_lower for sensitive in SENSITIVE_FIELD_NAMES):
                safe_copy[key] = "••••••••" if value else ""
            elif k_lower in ("connection_string", "uri", "mongouri", "mongo_uri"):
                safe_copy[key] = cls.mask_uri(str(value)) if value else ""
            elif isinstance(value, dict):
                safe_copy[key] = cls.redact_credentials(value)
            else:
                safe_copy[key] = value
        return safe_copy

    @classmethod
    def validate_external_url(cls, url: str) -> str:
        """
        Validates external URLs to prevent SSRF and protocol manipulation.
        Ensures valid scheme, non-empty host, and disallows dangerous schemes.
        """
        if not url:
            raise ValueError("URL cannot be empty.")
        clean_url = url.strip()
        parsed = urlparse(clean_url)
        if parsed.scheme.lower() not in ("http", "https"):
            raise ValueError(f"Invalid URL scheme '{parsed.scheme}'. Only 'http' and 'https' are permitted.")
        if not parsed.netloc:
            raise ValueError("Invalid URL: missing host authority.")
        host = parsed.hostname or ""
        if host.lower() in ("169.254.169.254", "metadata.google.internal"):
            raise ValueError("Access to cloud metadata endpoints is prohibited.")
        if host.lower() in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            raise ValueError("Internal or loopback addresses are not permitted.")
        return clean_url


# Convenience functional aliases
encrypt_credentials = EncryptionService.encrypt_payload
decrypt_credentials = EncryptionService.decrypt_payload
redact_sensitive_config = EncryptionService.redact_credentials
validate_external_url = EncryptionService.validate_external_url


def mask_secret(secret: str | None) -> str:
    """Masks secret with bullet dots."""
    return "••••••••" if secret else ""
