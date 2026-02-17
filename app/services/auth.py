from __future__ import annotations

import hashlib
import hmac
import secrets

PBKDF2_NAME = "pbkdf2_sha256"
PBKDF2_ITERATIONS = 120000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), PBKDF2_ITERATIONS)
    return f"{PBKDF2_NAME}${PBKDF2_ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        algo, iter_text, salt, expected = password_hash.split("$", 3)
    except ValueError:
        return False
    if algo != PBKDF2_NAME:
        return False
    try:
        iterations = int(iter_text)
    except ValueError:
        return False

    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), iterations)
    return hmac.compare_digest(digest.hex(), expected)
