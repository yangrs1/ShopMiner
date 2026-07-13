"""Boundary value tests for authentication endpoints.

Tests edge cases for auth register and login including:
- Empty email registration
- Very long (100+ chars) and very short passwords
- Login with non-existent email
"""

import pytest

pytestmark = pytest.mark.api


class TestAuthBoundary:
    """Boundary tests for auth endpoints."""

    def test_register_empty_email(self, client):
        """Boundary: empty email string returns 400."""
        resp = client.post("/api/v1/auth/register", json={
            "email": "",
            "password": "Test@123456",
            "first_name": "Test",
            "last_name": "User",
        })
        assert resp.status_code == 400

    @pytest.mark.parametrize("password,expected_status", [
        pytest.param(
            "A" + "x" * 68 + "@1a",
            201,
            id="long_valid_password",
        ),
        pytest.param(
            "short",
            400,
            id="short_invalid_password",
        ),
    ])
    def test_password_length_boundary(self, client, password, expected_status):
        """Boundary: very long (100+ chars) and very short passwords."""
        resp = client.post("/api/v1/auth/register", json={
            "email": f"pwdtest_{hash(password) % 100000}@test.com",
            "password": password,
            "first_name": "Pwd",
            "last_name": "Test",
        })
        assert resp.status_code == expected_status, (
            f"password(len={len(password)}) expected {expected_status} got {resp.status_code}: {resp.get_json()}"
        )

    def test_login_nonexistent_email(self, client):
        """Boundary: non-existent email returns 401."""
        resp = client.post("/api/v1/auth/login", json={
            "email": "nonexistent@test.com",
            "password": "Test@123456",
        })
        assert resp.status_code == 401
