"""Password hashing and policy (ADR-0026). Owned by T-026.

argon2id via ``argon2-cffi``, imported lazily inside the implementation.
"""

from __future__ import annotations

__all__ = ["check_password_policy", "hash_password", "needs_rehash", "verify_password"]


def hash_password(password: str) -> str:
    """argon2id hash with the ``argon2-cffi`` defaults (T-026)."""
    raise NotImplementedError("hash_password is implemented in T-026")


def verify_password(stored_hash: str, password: str) -> bool:
    """True when ``password`` matches ``stored_hash`` (T-026)."""
    raise NotImplementedError("verify_password is implemented in T-026")


def needs_rehash(stored_hash: str) -> bool:
    """True when the hash parameters are outdated (rehash on login) (T-026)."""
    raise NotImplementedError("needs_rehash is implemented in T-026")


def check_password_policy(password: str, *, email: str) -> None:
    """10-128 characters, not the email, not a common password; ``InvalidStateError`` with a
    friendly reason otherwise (T-026)."""
    raise NotImplementedError("check_password_policy is implemented in T-026")
