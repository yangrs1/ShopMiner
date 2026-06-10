"""Regression tests for order module bug fixes.

BUG-001: POST /orders message falsely claimed "paid" — verify message + status
BUG-005: Concurrency race condition in stock check/deduction
BUG-006: pay_order() returned 404 for another user's order instead of 403
"""
import pytest
from app.extensions import db
from app.models.order import Order
from app.models.product import Product


class TestBug001:
    """BUG-001: Order created message should say 'created', not 'paid'."""

    def test_order_message_is_pending_not_paid(self, client, auth_headers):
        """POST /orders creates a pending order — message must not say 'paid'."""
        # Arrange: add item to cart
        client.post("/api/v1/cart", headers=auth_headers, json={
            "product_id": 1, "quantity": 1,
        })

        # Act: create order
        resp = client.post("/api/v1/orders", headers=auth_headers)
        data = resp.get_json()

        # Assert: message says created (not paid)
        assert resp.status_code == 201
        assert data["message"] == "Order created successfully"
        # Assert: order status is pending, not paid
        assert data["data"]["status"] == "pending"


class TestBug005:
    """BUG-005: Concurrency race condition in stock deduction.

    NOTE: SQLite in-memory databases cannot safely handle concurrent writes
    from multiple threads.  True race-condition testing requires PostgreSQL
    with row-level locking (with_for_update()).  This test uses sequential
    multi-user requests to verify the critical invariant: total ordered items
    must never exceed available stock.
    """

    def test_concurrent_orders_dont_oversell(self, app, client, auth_headers):
        """Multiple users ordering the same product — stock never goes negative."""
        # --- Arrange -----------------------------------------------------------
        _set_stock(app, 1, 3)
        original_stock = 3

        # Register 5 users, each with 1 unit of product 1 in cart + sufficient balance
        tokens = _register_users_with_balance(app, client, 5)

        # --- Act: submit orders sequentially (SQLite limitation) ---------------
        created = 0
        rejected = 0
        for token in tokens:
            c = app.test_client()
            h = {"Authorization": f"Bearer {token}"}
            resp = c.post("/api/v1/orders", headers=h)
            if resp.status_code == 201:
                created += 1
            else:
                rejected += 1

        # --- Assert ------------------------------------------------------------
        # Invariant: total ordered <= original stock
        with app.app_context():
            product = db.session.get(Product, 1)
            assert product.stock >= 0, f"Stock negative: {product.stock}"
            assert product.stock + created == original_stock, (
                f"Stock {product.stock} + created {created} != original {original_stock}"
            )
            assert created == original_stock, (
                f"Only {created} orders created but stock was {original_stock}"
            )
            assert rejected == 2, (
                f"Expected 2 rejections, got {rejected}"
            )


class TestBug006:
    """BUG-006: pay_order() must return 403 for another user's order."""

    def test_pay_order_wrong_user_returns_403(self, client, auth_headers, app):
        """Paying another user's order must return 403."""
        # --- Arrange: create order as customer A --------------------------------
        client.post("/api/v1/cart", headers=auth_headers, json={
            "product_id": 1, "quantity": 1,
        })
        order_resp = client.post("/api/v1/orders", headers=auth_headers)
        order_id = order_resp.get_json()["data"]["id"]

        # Register customer B and get their token
        reg_resp = client.post("/api/v1/auth/register", json={
            "first_name": "Other", "last_name": "User",
            "email": "other_pay_test@test.com", "password": "Test@12345",
        })
        other_token = reg_resp.get_json()["data"]["access_token"]
        other_headers = {"Authorization": f"Bearer {other_token}"}

        # --- Act: customer B tries to pay customer A's order -------------------
        resp = client.post(f"/api/v1/orders/{order_id}/pay", headers=other_headers)
        data = resp.get_json()

        # --- Assert ------------------------------------------------------------
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {data}"
        assert "Access denied" in data["message"]

    def test_pay_order_not_found_returns_404(self, client, auth_headers):
        """Paying a non-existent order must return 404."""
        # Act: try to pay order 99999 (does not exist)
        resp = client.post("/api/v1/orders/99999/pay", headers=auth_headers)
        data = resp.get_json()

        # Assert
        assert resp.status_code == 404, f"Expected 404, got {resp.status_code}: {data}"
        assert "Order not found" in data["message"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_stock(app, product_id, stock):
    """Set a product's stock within an app context."""
    with app.app_context():
        product = db.session.get(Product, product_id)
        product.stock = stock
        db.session.commit()


def _register_users_with_balance(app, client, count):
    """Register *count* users, add product 1 to each cart, grant balance, return tokens."""
    from app.models.user import User

    tokens = []
    for i in range(count):
        email = f"concur_{i}@test.com"
        reg = client.post("/api/v1/auth/register", json={
            "first_name": f"User{i}", "last_name": "T",
            "email": email, "password": "Test@12345",
        })
        token = reg.get_json()["data"]["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        client.post("/api/v1/cart", headers=h, json={
            "product_id": 1, "quantity": 1,
        })
        tokens.append(token)

    # Grant sufficient balance to all new users
    with app.app_context():
        for u in User.query.filter(User.email.like("concur_%@test.com")).all():
            u.balance = 500000
        db.session.commit()

    return tokens
