import hmac
import hashlib
import time
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
import jwt

from app.core.config import settings
from app.core.encryption import EncryptionService
from app.core.security import JWT_ALGORITHM, JWT_SECRET_KEY


class SlackSecurityError(Exception):
    """Raised when Slack request verification or token handling fails."""
    pass


def verify_slack_signature(
    raw_body: bytes,
    timestamp_header: Optional[str],
    signature_header: Optional[str],
    signing_secret: Optional[str] = None,
    max_drift_seconds: int = 300,
) -> bool:
    """
    Verifies that an incoming HTTP request originated from Slack using HMAC-SHA256.
    
    1. Rejects if timestamp or signature is missing.
    2. Validates timestamp freshness (within 5 minutes) to protect against replay attacks.
    3. Computes HMAC-SHA256 signature against raw request body bytes.
    4. Uses constant-time hmac.compare_digest to prevent timing attacks.
    """
    secret = signing_secret or settings.slack_signing_secret
    if not secret:
        # If no secret configured in testing/dev, signature verification cannot pass
        return False

    if not timestamp_header or not signature_header:
        return False

    try:
        req_timestamp = int(timestamp_header)
    except (ValueError, TypeError):
        return False

    now_epoch = int(time.time())
    if abs(now_epoch - req_timestamp) > max_drift_seconds:
        # Replay attack prevention: timestamp is older or too far in the future
        return False

    # Base signature string format per Slack specification: v0:{timestamp}:{raw_body}
    sig_basestring = b"v0:" + str(req_timestamp).encode("utf-8") + b":" + raw_body
    computed_digest = hmac.new(
        secret.encode("utf-8"),
        sig_basestring,
        hashlib.sha256,
    ).hexdigest()
    expected_signature = f"v0={computed_digest}"

    return hmac.compare_digest(expected_signature, signature_header)


def encrypt_slack_bot_token(bot_token: str) -> str:
    """Encrypts a Slack bot access token using Fernet envelope encryption at rest."""
    if not bot_token:
        return ""
    return EncryptionService.encrypt_payload({"bot_token": bot_token})


def decrypt_slack_bot_token(encrypted_token: str) -> str:
    """Decrypts a persisted Slack bot token."""
    if not encrypted_token:
        return ""
    payload = EncryptionService.decrypt_payload(encrypted_token)
    return payload.get("bot_token", "")


def generate_slack_link_token(
    slack_team_id: str,
    slack_user_id: str,
    organization_id: str,
    expires_in_minutes: int = 15,
) -> str:
    """
    Generates a secure, signed, short-lived JWT for account linking.
    Binds the Slack User ID and Team ID to the target organization.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_in_minutes)
    payload = {
        "sub": f"slack_link_{slack_team_id}_{slack_user_id}",
        "slack_team_id": slack_team_id,
        "slack_user_id": slack_user_id,
        "organization_id": str(organization_id),
        "nonce": uuid.uuid4().hex,
        "type": "slack_account_link",
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_slack_link_token(token: str) -> Dict[str, Any]:
    """Validates and decodes an account linking token."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "slack_account_link":
            raise SlackSecurityError("Invalid token type for account linking.")
        return payload
    except jwt.ExpiredSignatureError:
        raise SlackSecurityError("Account linking token has expired. Please request a new link in Slack.")
    except Exception as e:
        raise SlackSecurityError(f"Invalid account linking token: {str(e)}")


def generate_oauth_state(
    organization_id: str,
    admin_user_id: str,
    expires_in_minutes: int = 10,
) -> str:
    """
    Generates a secure state token for Slack OAuth v2 installation initiation.
    Binds the installation to the initiating administrator and organization.
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_in_minutes)
    payload = {
        "sub": f"slack_oauth_{organization_id}",
        "organization_id": str(organization_id),
        "admin_user_id": str(admin_user_id),
        "nonce": uuid.uuid4().hex,
        "type": "slack_oauth_state",
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_oauth_state(state: str) -> Dict[str, Any]:
    """Validates and decodes an OAuth v2 state token."""
    try:
        payload = jwt.decode(state, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "slack_oauth_state":
            raise SlackSecurityError("Invalid state token type.")
        return payload
    except jwt.ExpiredSignatureError:
        raise SlackSecurityError("OAuth installation state has expired. Please restart the installation.")
    except Exception as e:
        raise SlackSecurityError(f"Invalid OAuth state: {str(e)}")


def resolve_slack_backend_url(request_host: Optional[str] = None, request_proto: Optional[str] = "https") -> str:
    """
    Resolves the canonical public base URL for Slack link cards and callbacks.
    Prioritizes active request host headers or SLACK_REDIRECT_URI origin over static frontend URLs.
    """
    if request_host:
        return f"{request_proto or 'https'}://{request_host}".rstrip("/")
    if getattr(settings, "slack_redirect_uri", None):
        import urllib.parse
        parsed = urllib.parse.urlparse(settings.slack_redirect_uri)
        if parsed.scheme and parsed.netloc:
            return f"{parsed.scheme}://{parsed.netloc}".rstrip("/")
    return getattr(settings, "trulin_public_url", "http://localhost:8000").rstrip("/")

