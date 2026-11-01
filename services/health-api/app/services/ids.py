import hashlib
import secrets


def generate_uhid() -> str:
    """Non-guessable Universal Health ID (public identifier, not a secret)."""
    return f"UHQ-{secrets.token_hex(8).upper()}"


def generate_qr_token() -> str:
    """Opaque QR payload — never embed PHI."""
    return secrets.token_urlsafe(32)


def hash_qr_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
