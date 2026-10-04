"""Basic auth helpers: salted password hashing and session tokens.

Deliberately minimal for this prototype - no email verification, no
password-reset links, no rate limiting. `hash_password`/`verify_password`
use PBKDF2 (stdlib, no extra dependency); tokens are opaque random strings
looked up in the `sessions` table (see store.py), not signed/stateless.
"""

import hashlib
import uuid

_ITERATIONS = 200_000


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or uuid.uuid4().hex
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), _ITERATIONS).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return hash_password(password, salt) == stored


def new_token() -> str:
    return uuid.uuid4().hex
