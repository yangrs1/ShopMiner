"""Tests for app.services.order_service.

Covers get_cart_items, create_order_from_cart, pay_order, cancel_order,
get_user_orders, confirm_delivery, get_order_with_access_check.
"""

import pytest
from app.extensions import db
from app.models.order import CartItem, Order
from app.models.user import User
from app.models.product import Product

pytestmark = pytest.mark.unit


class TestOrderService:
    """Service-layer tests for order_service."""

    # ── get_cart_items ───────────────────────────────────────────

    def test_get_cart_items_empty(self, app, order_service, sample_user):
        """New user has an empty cart."""
        items = order_service.get_cart_items(sample_user.id)
        assert items == []

    def test_get_cart_items_with_items(self, app, order_service, sample_user, sample_product):
        """User with cart items gets them back."""
        cart = CartItem(user_id=sample_user.id, product_id=sample_product.id, quantity=2)
        db.session.add(cart)
        db.session.commit()

        items = order_service.get_cart_items(sample_user.id)
        assert len(items) == 1
        assert items[0].product_id == sample_product.id
        assert items[0].quantity == 2

    # ── create_order_from_cart ───────────────────────────────────

    def test_create_order_from_cart_success(self, app, order_service, sample_user, sample_product):
        """Creating an order with cart items succeeds and clears the cart."""
        cart = CartItem(user_id=sample_user.id, product_id=sample_product.id, quantity=1)
        db.session.add(cart)
        db.session.commit()

        order, err = order_service.create_order_from_cart(
            sample_user.id,
            shipping_address="123 Test St",
            shipping_phone="13800138000",
        )
        assert order is not None
        assert err is None
        assert order.total_amount == sample_product.price  # 1 * 2999
        assert order.shipping_address == "123 Test St"
        assert order.shipping_phone == "13800138000"

        # Cart should be cleared
        remaining = order_service.get_cart_items(sample_user.id)
        assert remaining == []

    def test_create_order_empty_cart_returns_error(self, app, order_service, sample_user):
        """Creating an order with empty cart returns error."""
        order, err = order_service.create_order_from_cart(sample_user.id)
        assert order is None
        assert err == "Cart is empty"

    def test_create_order_insufficient_stock(self, app, order_service, sample_user, sample_product):
        """Creating an order when stock < quantity returns error."""
        cart = CartItem(user_id=sample_user.id, product_id=sample_product.id, quantity=9999)
        db.session.add(cart)
        db.session.commit()

        order, err = order_service.create_order_from_cart(sample_user.id)
        assert order is None
        assert "Insufficient stock" in err

    def test_create_order_insufficient_balance(self, app, order_service, sample_user, sample_product):
        """Creating an order when balance < total returns error."""
        # Use a fresh query to modify balance in the current session
        user = db.session.get(User, sample_user.id)
        user.balance = 10
        db.session.commit()

        cart = CartItem(user_id=sample_user.id, product_id=sample_product.id, quantity=1)
        db.session.add(cart)
        db.session.commit()

        order, err = order_service.create_order_from_cart(sample_user.id)
        assert order is None
        assert "Insufficient balance" in err

    # ── pay_order ────────────────────────────────────────────────

    def test_pay_order_success(self, app, order_service, sample_user, sample_order):
        """Paying a pending order updates status to paid and deducts balance."""
        order, err = order_service.pay_order(sample_user.id, sample_order.id)
        assert order is not None
        assert err is None
        assert order.status == Order.STATUS_PAID

        # Query fresh user from db to avoid session-staleness issues
        fresh_user = db.session.get(User, sample_user.id)
        expected_balance = 50000 - sample_order.total_amount
        assert fresh_user.balance == expected_balance

    def test_pay_order_insufficient_balance(self, app, order_service, sample_user, sample_order):
        """Can't pay an order with insufficient balance."""
        # Use a fresh query to modify balance in the current session
        user = db.session.get(User, sample_user.id)
        user.balance = 100
        db.session.commit()

        order, err = order_service.pay_order(sample_user.id, sample_order.id)
        assert order is None
        assert "Insufficient balance" in err

    def test_pay_order_not_found(self, app, order_service, sample_user):
        """Paying a nonexistent order returns error."""
        order, err = order_service.pay_order(sample_user.id, 99999)
        assert order is None
        assert err == "Order not found"

    def test_pay_order_access_denied(self, app, order_service, sample_order):
        """Paying another user's order returns access denied."""
        order, err = order_service.pay_order(99999, sample_order.id)
        assert order is None
        assert err == "Access denied"

    # ── cancel_order ─────────────────────────────────────────────

    def test_cancel_pending_order_restores_stock(self, app, order_service, sample_user,
                                                  sample_order, sample_product):
        """Cancelling a pending order restores product stock."""
        # Use a fresh query to avoid session-staleness with fixture objects
        fresh_product = db.session.get(Product, sample_product.id)
        before_stock = fresh_product.stock

        order, err = order_service.cancel_order(sample_user.id, sample_order.id)
        assert order is not None
        assert err is None
        assert order.status == Order.STATUS_CANCELLED

        # Query a fresh copy of the product after cancellation
        after_product = db.session.get(Product, sample_product.id)
        # sample_order has 2 items, so stock increases by 2
        assert after_product.stock == before_stock + 2

    def test_cancel_order_not_found(self, app, order_service, sample_user):
        """Cancelling a nonexistent order returns error."""
        order, err = order_service.cancel_order(sample_user.id, 99999)
        assert order is None
        assert err == "Order not found"

    def test_cancel_order_access_denied(self, app, order_service, sample_order):
        """Cancelling another user's order returns access denied."""
        order, err = order_service.cancel_order(99999, sample_order.id)
        assert order is None
        assert err == "Access denied"

    # ── get_user_orders ──────────────────────────────────────────

    def test_get_user_orders_pagination(self, app, order_service, sample_user, sample_order):
        """get_user_orders returns a pagination object with the order."""
        pagination = order_service.get_user_orders(sample_user.id, page=1, per_page=20)
        assert pagination is not None
        assert pagination.total == 1
        assert len(pagination.items) == 1
        assert pagination.items[0].id == sample_order.id

    def test_get_user_orders_empty(self, app, order_service, sample_user):
        """User with no orders gets empty pagination."""
        pagination = order_service.get_user_orders(sample_user.id)
        assert pagination.total == 0
        assert pagination.items == []

    # ── confirm_delivery ─────────────────────────────────────────

    def test_confirm_delivery_fails_for_pending_order(self, app, order_service,
                                                       sample_user, sample_order):
        """confirm_delivery fails when order status is not 'shipped'."""
        order, err = order_service.confirm_delivery(sample_user.id, sample_order.id)
        assert order is None
        assert "Cannot confirm delivery" in err

    def test_confirm_delivery_success(self, app, order_service, sample_user, sample_order):
        """A shipped order can be confirmed as delivered."""
        # Manually transition to shipped (no service function for this)
        order_rec = db.session.get(Order, sample_order.id)
        order_rec.status = Order.STATUS_SHIPPED
        db.session.commit()

        order, err = order_service.confirm_delivery(sample_user.id, sample_order.id)
        assert order is not None
        assert err is None
        assert order.status == Order.STATUS_DELIVERED

    # ── get_order_with_access_check ──────────────────────────────

    def test_get_order_with_access_check_own_order(self, app, order_service,
                                                     sample_user, sample_order):
        """User can access their own order."""
        order, err = order_service.get_order_with_access_check(
            sample_order.id, sample_user.id,
        )
        assert order is not None
        assert err is None
        assert order.id == sample_order.id

    def test_get_order_with_access_check_other_user(self, app, order_service,
                                                     sample_order):
        """Another (non-admin) user cannot access someone else's order.

        Note: We create a second real user here rather than passing a
        non-existent ID, because the service code calls ``user.role``
        and would crash with AttributeError on ``None``.
        """
        other = User(
            email="other_user@test.com", first_name="Other", last_name="User",
        )
        other.set_password("TestPass123")
        db.session.add(other)
        db.session.commit()

        order, err = order_service.get_order_with_access_check(
            sample_order.id, other.id,
        )
        assert order is None
        assert err == "Access denied"

    def test_get_order_with_access_check_not_found(self, app, order_service, sample_user):
        """Nonexistent order returns not found."""
        order, err = order_service.get_order_with_access_check(99999, sample_user.id)
        assert order is None
        assert err == "Order not found"
