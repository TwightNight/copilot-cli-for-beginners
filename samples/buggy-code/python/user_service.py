# user_service.py - Sample code with intentional bugs for practice
# Use this file to practice code review and debugging with GitHub Copilot CLI
#
# Try these commands:
#   copilot --allow-all -p "Review @samples/buggy-code/python/user_service.py for security issues"
#   copilot --allow-all -p "Find all bugs in @samples/buggy-code/python/user_service.py"

from __future__ import annotations

import base64
from collections.abc import Mapping
from contextlib import closing
from dataclasses import dataclass
import hashlib
import hmac
import os
import pickle
import sqlite3
from typing import Any


DB_PATH = "users.db"
MAX_PASSWORD_BYTES = 1024
PASSWORD_ITERATIONS = 600_000


class DuplicateEmailError(ValueError):
    """Raised when an account already exists for an email address."""


class AuthorizationError(PermissionError):
    """Raised when an actor cannot perform the requested operation."""


@dataclass(frozen=True)
class Actor:
    user_id: int
    is_admin: bool = False


def get_connection() -> sqlite3.Connection:
    """Open a configured database connection."""
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def require_string(data: Mapping[str, object], field: str) -> str:
    """Read a required string field from user input."""
    value = data.get(field)
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    return value


def validate_user_id(user_id: object) -> int:
    """Validate a positive integer user ID."""
    if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id <= 0:
        raise ValueError("user_id must be a positive integer")
    return user_id


def validate_name(name: str) -> str:
    """Validate and normalize a display name."""
    value = name.strip()
    if not value or len(value) > 100:
        raise ValueError("name must contain 1-100 characters")
    return value


def validate_email(email: str) -> str:
    """Validate and normalize an email address."""
    value = email.strip().casefold()
    if not value or len(value) > 254 or "@" not in value:
        raise ValueError("email is invalid")
    return value


def validate_password(password: str) -> str:
    """Validate a password without truncating it."""
    if not password:
        raise ValueError("password must not be empty")
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError("password is too long")
    return password


def get_user(user_id: int) -> sqlite3.Row | None:
    """Return a user's public fields by ID."""
    user_id = validate_user_id(user_id)

    with closing(get_connection()) as connection:
        return connection.execute(
            """
            SELECT id, name, email
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()


# BUG 2: Race Condition
# Multiple requests can trigger parallel database calls before cache is set
user_cache: dict[int, sqlite3.Row | None] = {}


def get_cached_user(user_id: int) -> sqlite3.Row | None:
    """Return a cached user record."""
    user_id = validate_user_id(user_id)
    if user_id not in user_cache:
        user_cache[user_id] = get_user(user_id)
    return user_cache[user_id]


def update_user(user_id: int, data: Mapping[str, object]) -> sqlite3.Row | None:
    """Update a user's name and return the updated public record."""
    user_id = validate_user_id(user_id)
    name = validate_name(require_string(data, "name"))

    with closing(get_connection()) as connection:
        with connection:
            cursor = connection.execute(
                "UPDATE users SET name = ? WHERE id = ?",
                (name, user_id),
            )
            if cursor.rowcount != 1:
                return None

        updated_user = connection.execute(
            """
            SELECT id, name, email
            FROM users
            WHERE id = ?
            """,
            (user_id,),
        ).fetchone()

    user_cache.pop(user_id, None)
    return updated_user


def login(email: str, password: str) -> dict[str, Any]:
    """Authenticate a user without logging or returning credentials."""
    email = validate_email(email)
    password = validate_password(password)

    with closing(get_connection()) as connection:
        user = connection.execute(
            """
            SELECT id, name, email, password_hash
            FROM users
            WHERE email = ?
            """,
            (email,),
        ).fetchone()

    if user is None or not verify_password(password, user["password_hash"]):
        return {"success": False}

    return {
        "success": True,
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
        },
    }


def verify_password(input_password: str, stored_password: str) -> bool:
    """Verify a PBKDF2 password hash using a constant-time comparison."""
    try:
        algorithm, iterations_text, salt_text, digest_text = stored_password.split(
            "$",
            3,
        )
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_text)
        salt = base64.b64decode(salt_text, validate=True)
        expected_digest = base64.b64decode(digest_text, validate=True)
    except (TypeError, ValueError):
        return False

    candidate_digest = hashlib.pbkdf2_hmac(
        "sha256",
        validate_password(input_password).encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(candidate_digest, expected_digest)


def create_user(user_data: Mapping[str, object]) -> int:
    """Create a user with a parameterized insert and password hash."""
    name = validate_name(require_string(user_data, "name"))
    email = validate_email(require_string(user_data, "email"))
    password = validate_password(require_string(user_data, "password"))
    password_hash = hash_password(password)

    with closing(get_connection()) as connection:
        try:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO users (name, email, password_hash)
                    VALUES (?, ?, ?)
                    """,
                    (name, email, password_hash),
                )
        except sqlite3.IntegrityError as error:
            if "users.email" not in str(error):
                raise
            raise DuplicateEmailError(
                "an account already exists for that email"
            ) from error

    return int(cursor.lastrowid)


# BUG 7: Hardcoded Secret
# JWT secret should be in environment variables
JWT_SECRET = "super-secret-key-12345"

def generate_token(user_id: int) -> str:
    import jwt
    return jwt.encode({"user_id": user_id}, JWT_SECRET, algorithm="HS256")


def delete_user(target_user_id: int, actor: Actor) -> bool:
    """Delete a user only when the authenticated actor is authorized."""
    target_user_id = validate_user_id(target_user_id)
    actor_user_id = validate_user_id(actor.user_id)

    if not actor.is_admin and actor_user_id != target_user_id:
        raise AuthorizationError("not authorized to delete this user")

    with closing(get_connection()) as connection:
        with connection:
            cursor = connection.execute(
                "DELETE FROM users WHERE id = ?",
                (target_user_id,),
            )
            deleted = cursor.rowcount == 1

    if deleted:
        user_cache.pop(target_user_id, None)
    return deleted


def hash_password(password: str) -> str:
    """Hash a password with a salted, deliberately slow PBKDF2 derivation."""
    password = validate_password(password)
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    salt_text = base64.b64encode(salt).decode("ascii")
    digest_text = base64.b64encode(digest).decode("ascii")
    return f"pbkdf2_sha256${PASSWORD_ITERATIONS}${salt_text}${digest_text}"


# BUG 10: Pickle Deserialization (Python-specific)
# Deserializing untrusted data with pickle is dangerous
def load_user_preferences(encoded_data: str) -> Any:
    decoded = base64.b64decode(encoded_data)
    return pickle.loads(decoded)  # Remote code execution vulnerability!
