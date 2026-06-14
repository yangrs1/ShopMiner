"""Tests for app.services.auth_service.

Covers register_user, authenticate_user, get_user_by_id, generate_token.
"""

import pytest
from app.extensions import db

pytestmark = pytest.mark.unit


class TestAuthService:
    """Service-layer tests for auth_service."""

    # ── register_user ─────────────────────────────────────────────

    def test_register_user_success(self, app, auth_service):
        """Register a valid new user returns the user with no error."""
        user, err = auth_service.register_user(
            email="new@test.com", password="ValidPass1",
            first_name="New", last_name="User",
        )
        assert user is not None
        assert err is None
        assert user.email == "new@test.com"
        assert user.first_name == "New"
        assert user.last_name == "User"

    def test_register_duplicate_email(self, app, auth_service, sample_user):
        """Registering with an existing email returns an error."""
        user, err = auth_service.register_user(
            email="svc_test@shopminer.com", password="OtherPass1",
            first_name="Dup", last_name="User",
        )
        assert user is None
        assert err == "Email already registered"

    def test_register_weak_password(self, app, auth_service):
        """Password without uppercase returns an error."""
        user, err = auth_service.register_user(
            email="weak@test.com", password="weakpass1",
            first_name="Weak", last_name="Pass",
        )
        assert user is None
        assert err == "Password must be at least 8 characters with uppercase, lowercase and digit"

    def test_register_no_digit(self, app, auth_service):
        """Password without digit returns an error."""
        user, err = auth_service.register_user(
            email="nodigit@test.com", password="NoDigitPass",
            first_name="No", last_name="Digit",
        )
        assert user is None
        assert err == "Password must be at least 8 characters with uppercase, lowercase and digit"

    def test_register_too_short(self, app, auth_service):
        """Password shorter than 8 characters returns an error."""
        user, err = auth_service.register_user(
            email="short@test.com", password="Sh1",
            first_name="Too", last_name="Short",
        )
        assert user is None
        assert err == "Password must be at least 8 characters with uppercase, lowercase and digit"

    def test_register_empty_address_default(self, app, auth_service):
        """When address is not provided, it defaults to empty string."""
        user, err = auth_service.register_user(
            email="addr@test.com", password="ValidPass1",
            first_name="Addr", last_name="Test",
        )
        assert user is not None
        assert err is None
        assert user.address == ""

    def test_register_icon_default(self, app, auth_service):
        """When icon is not provided, it defaults to icon_bear.png."""
        user, err = auth_service.register_user(
            email="icon@test.com", password="ValidPass1",
            first_name="Icon", last_name="Test",
        )
        assert user is not None
        assert err is None
        assert user.icon == "icon_bear.png"

    # ── authenticate_user ────────────────────────────────────────

    def test_authenticate_success(self, app, auth_service, sample_user):
        """Valid credentials return the user."""
        user = auth_service.authenticate_user("svc_test@shopminer.com", "TestPass123")
        assert user is not None
        assert user.id == sample_user.id
        assert user.email == "svc_test@shopminer.com"

    def test_authenticate_wrong_password(self, app, auth_service, sample_user):
        """Invalid password returns None."""
        user = auth_service.authenticate_user("svc_test@shopminer.com", "WrongPass1")
        assert user is None

    def test_authenticate_nonexistent_email(self, app, auth_service):
        """Email that does not exist returns None."""
        user = auth_service.authenticate_user("nobody@nowhere.com", "SomePass1")
        assert user is None

    # ── get_user_by_id ───────────────────────────────────────────

    def test_get_user_by_id_returns_user(self, app, auth_service, sample_user):
        """Looking up an existing ID returns the user."""
        user = auth_service.get_user_by_id(sample_user.id)
        assert user is not None
        assert user.email == "svc_test@shopminer.com"

    def test_get_user_by_id_nonexistent(self, app, auth_service):
        """Looking up a nonexistent ID returns None."""
        user = auth_service.get_user_by_id(99999)
        assert user is None

    # ── generate_token ───────────────────────────────────────────

    def test_generate_token_returns_string(self, app, auth_service, sample_user):
        """generate_token returns a JWT string."""
        token = auth_service.generate_token(sample_user)
        assert isinstance(token, str)
        assert len(token) > 20
        # JWT has three dot-separated parts
        assert token.count(".") == 2
