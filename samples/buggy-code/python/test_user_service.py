import sqlite3
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).parent))

import user_service


@pytest.fixture
def database_path(tmp_path, monkeypatch):
    """Create an isolated users database for each test."""
    path = tmp_path / "users.db"
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            )
            """
        )
        connection.commit()
    finally:
        connection.close()

    monkeypatch.setattr(user_service, "DB_PATH", str(path))
    monkeypatch.setattr(user_service, "PASSWORD_ITERATIONS", 1_000)
    user_service.user_cache.clear()
    return path


def read_users(path):
    """Return users ordered by ID for database-state assertions."""
    connection = sqlite3.connect(path)
    try:
        return connection.execute(
            "SELECT id, name, email FROM users ORDER BY id"
        ).fetchall()
    finally:
        connection.close()


@pytest.fixture
def created_user(database_path):
    """Create one valid user and return its ID and password."""
    password = "correct horse battery staple"
    user_id = user_service.create_user(
        {
            "name": "Alice",
            "email": "Alice@example.com",
            "password": password,
        }
    )
    return user_id, password


class TestValidation:
    """Tests for service-boundary validation."""

    @pytest.mark.parametrize("value", [0, -1, True, "1", None])
    def test_validate_user_id_rejects_invalid_values(self, value):
        with pytest.raises(ValueError, match="positive integer"):
            user_service.validate_user_id(value)

    @pytest.mark.parametrize("value", ["", "   ", None])
    def test_validate_name_rejects_empty_values(self, value):
        with pytest.raises((AttributeError, ValueError)):
            user_service.validate_name(value)

    def test_validate_name_rejects_values_over_limit(self):
        with pytest.raises(ValueError, match="1-100"):
            user_service.validate_name("a" * 101)

    @pytest.mark.parametrize("value", ["", "invalid-email", None])
    def test_validate_email_rejects_invalid_values(self, value):
        with pytest.raises((AttributeError, ValueError)):
            user_service.validate_email(value)

    def test_validate_password_rejects_oversized_values(self):
        with pytest.raises(ValueError, match="too long"):
            user_service.validate_password("p" * (user_service.MAX_PASSWORD_BYTES + 1))


class TestPasswordFunctions:
    """Tests for password hashing and verification."""

    def test_hash_password_verifies_original_password(self, database_path):
        password_hash = user_service.hash_password("secret")

        assert user_service.verify_password("secret", password_hash) is True

    def test_verify_password_rejects_wrong_password(self, database_path):
        password_hash = user_service.hash_password("secret")

        assert user_service.verify_password("wrong", password_hash) is False

    def test_hash_password_uses_a_unique_salt(self, database_path):
        first_hash = user_service.hash_password("secret")
        second_hash = user_service.hash_password("secret")

        assert first_hash != second_hash

    def test_verify_password_rejects_malformed_hash(self, database_path):
        assert user_service.verify_password("secret", "not-a-hash") is False


class TestUserCrud:
    """Tests for parameterized user CRUD methods."""

    def test_create_user_stores_hash_and_normalizes_email(self, database_path):
        user_id = user_service.create_user(
            {
                "name": "O'Reilly",
                "email": " USER@example.COM ",
                "password": "secret",
            }
        )

        assert user_id == 1
        assert read_users(database_path) == [
            (1, "O'Reilly", "user@example.com")
        ]
        connection = sqlite3.connect(database_path)
        try:
            stored_hash = connection.execute(
                "SELECT password_hash FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()[0]
        finally:
            connection.close()
        assert stored_hash != "secret"

    def test_create_user_rejects_duplicate_email(self, created_user):
        with pytest.raises(user_service.DuplicateEmailError):
            user_service.create_user(
                {
                    "name": "Another User",
                    "email": "ALICE@example.com",
                    "password": "another password",
                }
            )

    def test_get_user_returns_public_fields_only(self, created_user):
        user_id, _ = created_user

        user = user_service.get_user(user_id)

        assert dict(user) == {
            "id": user_id,
            "name": "Alice",
            "email": "alice@example.com",
        }

    @pytest.mark.parametrize("payload", ["1 OR 1=1", "1; DELETE FROM users; --"])
    def test_get_user_rejects_sql_injection_payloads(
        self,
        database_path,
        payload,
    ):
        with pytest.raises(ValueError):
            user_service.get_user(payload)

        assert read_users(database_path) == []

    def test_update_user_preserves_apostrophes(self, created_user):
        user_id, _ = created_user

        updated_user = user_service.update_user(
            user_id,
            {"name": "O'Reilly"},
        )

        assert dict(updated_user)["name"] == "O'Reilly"

    def test_update_user_returns_none_for_missing_user(self, database_path):
        assert user_service.update_user(999, {"name": "Nobody"}) is None

    def test_delete_user_returns_false_for_missing_user(
        self,
        database_path,
    ):
        assert user_service.delete_user(999, user_service.Actor(999)) is False


class TestAuthentication:
    """Tests for login behavior."""

    def test_login_succeeds_with_valid_credentials(self, created_user):
        _, password = created_user

        result = user_service.login("ALICE@example.com", password)

        assert result == {
            "success": True,
            "user": {
                "id": 1,
                "name": "Alice",
                "email": "alice@example.com",
            },
        }

    def test_login_rejects_wrong_password(self, created_user):
        result = user_service.login("alice@example.com", "wrong password")

        assert result == {"success": False}

    def test_login_rejects_sql_injection_email(self, database_path):
        with pytest.raises(ValueError, match="email"):
            user_service.login("' OR 1=1 --", "anything")


class TestAuthorization:
    """Tests for deletion authorization."""

    def test_delete_user_rejects_different_non_admin_actor(self, created_user):
        user_id, _ = created_user

        with pytest.raises(user_service.AuthorizationError):
            user_service.delete_user(user_id, user_service.Actor(user_id + 1))

    def test_delete_user_allows_owner_and_clears_cache(self, created_user):
        user_id, _ = created_user
        user_service.get_cached_user(user_id)

        deleted = user_service.delete_user(user_id, user_service.Actor(user_id))

        assert deleted is True
        assert user_service.get_user(user_id) is None
        assert user_id not in user_service.user_cache

    def test_delete_user_allows_admin_to_delete_other_user(self, created_user):
        user_id, _ = created_user

        assert user_service.delete_user(
            user_id,
            user_service.Actor(user_id + 1, is_admin=True),
        ) is True


def test_crud_and_login_work_together(created_user):
    user_id, password = created_user

    user_service.update_user(user_id, {"name": "Updated Alice"})
    result = user_service.login("alice@example.com", password)

    assert result["success"] is True
    assert result["user"]["name"] == "Updated Alice"
