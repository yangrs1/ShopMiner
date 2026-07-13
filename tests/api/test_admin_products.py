"""Tests for admin product management API."""
import json
import pytest
from app.extensions import db


class TestAdminProducts:
    """Admin product management endpoints."""

    def test_list_all_products(self, client, admin_headers):
        """Admin can list all products including inactive."""
        resp = client.get("/api/v1/admin/products", headers=admin_headers)
        json = resp.get_json()
        assert resp.status_code == 200
        assert "products" in json["data"]
        assert json["data"]["total"] >= 0

    def test_list_products_pagination(self, client, admin_headers):
        """Admin product list supports pagination."""
        resp = client.get("/api/v1/admin/products?page=1&per_page=5", headers=admin_headers)
        json = resp.get_json()
        assert resp.status_code == 200
        assert json["data"]["page"] == 1
        assert len(json["data"]["products"]) <= 5

    def test_list_products_forbidden_for_user(self, client, auth_headers):
        """Regular user gets 403."""
        resp = client.get("/api/v1/admin/products", headers=auth_headers)
        assert resp.status_code == 403

    def test_get_product_detail(self, client, admin_headers):
        """Admin can get product detail."""
        resp = client.get("/api/v1/admin/products/1", headers=admin_headers)
        json = resp.get_json()
        assert resp.status_code == 200
        assert json["data"]["id"] == 1

    def test_create_product(self, client, admin_headers):
        """Admin can create a product."""
        # [GAP: missing-test]
        resp = client.post("/api/v1/admin/products", headers=admin_headers, json={
            "name": "New Test Product",
            "price": 1999,
            "stock": 50,
            "description": "A brand new test product",
            "category_name": "test",
        })
        json = resp.get_json()
        assert resp.status_code == 200
        assert json["message"] == "Product created"
        assert json["data"]["name"] == "New Test Product"
        assert json["data"]["price"] == 1999
        assert json["data"]["stock"] == 50
        assert json["data"]["is_active"] is True

    def test_create_product_missing_name(self, client, admin_headers):
        """Creating a product without name returns 400."""
        # [GAP: missing-test]
        resp = client.post("/api/v1/admin/products", headers=admin_headers, json={
            "price": 1999,
        })
        assert resp.status_code == 400
        assert "name is required" in resp.get_json()["message"]

    def test_update_product(self, client, admin_headers):
        """Admin can update a product."""
        # [GAP: missing-test]
        resp = client.put("/api/v1/admin/products/1", headers=admin_headers, json={
            "name": "Updated T-Shirt",
            "price": 2499,
            "stock": 80,
        })
        json = resp.get_json()
        assert resp.status_code == 200
        assert json["message"] == "Product updated"
        assert json["data"]["name"] == "Updated T-Shirt"
        assert json["data"]["price"] == 2499
        assert json["data"]["stock"] == 80

    def test_toggle_product_active(self, client, admin_headers):
        """Admin can toggle product active status."""
        # [GAP: missing-test]
        resp = client.put("/api/v1/admin/products/1/toggle-active", headers=admin_headers)
        json = resp.get_json()
        assert resp.status_code == 200
        assert json["data"]["is_active"] is False
        assert "deactivated" in json["message"]

        resp2 = client.put("/api/v1/admin/products/1/toggle-active", headers=admin_headers)
        json2 = resp2.get_json()
        assert resp2.status_code == 200
        assert json2["data"]["is_active"] is True
        assert "activated" in json2["message"]

    # ── Additional admin product tests ────────────────────────

    def test_get_product_detail_not_found(self, client, admin_headers):
        """[GAP: missing-test] Getting a non-existent product returns 404."""
        resp = client.get("/api/v1/admin/products/99999", headers=admin_headers)
        assert resp.status_code == 404
        assert "not found" in resp.get_json()["message"]

    def test_list_products_with_search(self, client, admin_headers):
        """[GAP: missing-test] Admin can search products by name."""
        resp = client.get('/api/v1/admin/products?q=T-Shirt', headers=admin_headers)
        json = resp.get_json()
        assert resp.status_code == 200
        # At least one product matching "T-Shirt" in name
        assert any("T-Shirt" in p["name"] for p in json["data"]["products"])

    def test_list_products_with_search_description(self, client, admin_headers):
        """[GAP: missing-test] Admin can search products by description."""
        resp = client.get('/api/v1/admin/products?q=test+t-shirt', headers=admin_headers)
        json = resp.get_json()
        assert resp.status_code == 200
        assert json["data"]["total"] >= 1

    def test_list_products_filter_active(self, client, admin_headers):
        """[GAP: missing-test] Admin can filter by is_active=true."""
        resp = client.get('/api/v1/admin/products?is_active=1', headers=admin_headers)
        json = resp.get_json()
        assert resp.status_code == 200
        for p in json["data"]["products"]:
            assert p["is_active"] is True

    def test_list_products_filter_inactive(self, client, admin_headers):
        """[GAP: missing-test] Admin can filter by is_active=false."""
        resp = client.get('/api/v1/admin/products?is_active=0', headers=admin_headers)
        json = resp.get_json()
        assert resp.status_code == 200
        for p in json["data"]["products"]:
            assert p["is_active"] is False

    def test_create_product_bad_price_not_int(self, client, admin_headers):
        """[GAP: missing-test] Creating product with non-int price returns 400."""
        resp = client.post("/api/v1/admin/products", headers=admin_headers, json={
            "name": "Bad Price",
            "price": "nineteen",
            "stock": 10,
        })
        assert resp.status_code == 400
        assert "Price" in resp.get_json()["message"]

    def test_create_product_bad_price_negative(self, client, admin_headers):
        """[GAP: missing-test] Creating product with negative price returns 400."""
        resp = client.post("/api/v1/admin/products", headers=admin_headers, json={
            "name": "Neg Price",
            "price": -100,
            "stock": 10,
        })
        assert resp.status_code == 400
        assert "Price" in resp.get_json()["message"]

    def test_create_product_bad_stock_type(self, client, admin_headers):
        """[GAP: missing-test] Creating product with non-int stock returns 400."""
        resp = client.post("/api/v1/admin/products", headers=admin_headers, json={
            "name": "Bad Stock",
            "price": 1999,
            "stock": "fifty",
        })
        assert resp.status_code == 400
        assert "Stock" in resp.get_json()["message"]

    def test_create_product_bad_stock_negative(self, client, admin_headers):
        """[GAP: missing-test] Creating product with negative stock returns 400."""
        resp = client.post("/api/v1/admin/products", headers=admin_headers, json={
            "name": "Neg Stock",
            "price": 1999,
            "stock": -1,
        })
        assert resp.status_code == 400
        assert "Stock" in resp.get_json()["message"]

    def test_update_product_not_found(self, client, admin_headers):
        """[GAP: missing-test] Updating a non-existent product returns 404."""
        resp = client.put("/api/v1/admin/products/99999", headers=admin_headers, json={
            "name": "Ghost",
        })
        assert resp.status_code == 404
        assert "not found" in resp.get_json()["message"]

    def test_update_product_bad_price(self, client, admin_headers):
        """[GAP: missing-test] Updating product with bad price returns 400."""
        resp = client.put("/api/v1/admin/products/1", headers=admin_headers, json={
            "price": -50,
        })
        assert resp.status_code == 400
        assert "Price" in resp.get_json()["message"]

    def test_update_product_bad_stock(self, client, admin_headers):
        """[GAP: missing-test] Updating product with bad stock returns 400."""
        resp = client.put("/api/v1/admin/products/1", headers=admin_headers, json={
            "stock": -5,
        })
        assert resp.status_code == 400
        assert "Stock" in resp.get_json()["message"]

    def test_update_product_empty_name(self, client, admin_headers):
        """[GAP: missing-test] Updating product with empty name returns 400."""
        resp = client.put("/api/v1/admin/products/1", headers=admin_headers, json={
            "name": "",
        })
        assert resp.status_code == 400
        assert "name cannot be empty" in resp.get_json()["message"]

    def test_toggle_product_active_not_found(self, client, admin_headers):
        """[GAP: missing-test] Toggling a non-existent product returns 404."""
        resp = client.put("/api/v1/admin/products/99999/toggle-active",
                          headers=admin_headers)
        assert resp.status_code == 404
        assert "not found" in resp.get_json()["message"]

    def test_update_product_all_fields(self, client, admin_headers):
        """[GAP: missing-test] Updating product with all optional fields."""
        resp = client.put("/api/v1/admin/products/1", headers=admin_headers, json={
            "description": "Updated desc",
            "image": "/img/new.webp",
            "type": "electronic",
            "category_name": "数码产品",
        })
        json = resp.get_json()
        assert resp.status_code == 200
        assert json["data"]["description"] == "Updated desc"
        assert json["data"]["type"] == "electronic"
        assert json["data"]["category_name"] == "数码产品"

    # ── Admin order/user edge cases (not covered by YAML) ────

    def test_ship_order_unauthorized(self, client, auth_headers):
        """[GAP: missing-test] Ship order without admin returns 403."""
        resp = client.put("/api/v1/admin/orders/1/ship", headers=auth_headers)
        assert resp.status_code == 403

    def test_ship_order_not_found(self, client, admin_headers):
        """[GAP: missing-test] Ship non-existent order returns 404."""
        resp = client.put("/api/v1/admin/orders/99999/ship", headers=admin_headers)
        assert resp.status_code == 404

    def test_deliver_order_unauthorized(self, client, auth_headers):
        """[GAP: missing-test] Deliver order without admin returns 403."""
        resp = client.put("/api/v1/admin/orders/1/deliver", headers=auth_headers)
        assert resp.status_code == 403

    def test_deliver_order_not_found(self, client, admin_headers):
        """[GAP: missing-test] Deliver non-existent order returns 404."""
        resp = client.put("/api/v1/admin/orders/99999/deliver", headers=admin_headers)
        assert resp.status_code == 404

    def test_refund_order_unauthorized(self, client, auth_headers):
        """[GAP: missing-test] Refund order without admin returns 403."""
        resp = client.post("/api/v1/admin/orders/1/refund", headers=auth_headers)
        assert resp.status_code == 403

    def test_refund_order_not_found(self, client, admin_headers):
        """[GAP: missing-test] Refund non-existent order returns 404."""
        resp = client.post("/api/v1/admin/orders/99999/refund", headers=admin_headers)
        assert resp.status_code == 404

    def test_adjust_balance_non_numeric(self, client, admin_headers):
        """[GAP: missing-test] Adjust balance with non-numeric amount returns 400."""
        resp = client.put("/api/v1/admin/users/2/balance", headers=admin_headers, json={
            "amount": "abc",
        })
        assert resp.status_code == 400
        assert "must be a number" in resp.get_json()["message"]

    def test_admin_pay_order_paid_order(self, client, admin_headers, auth_headers):
        """[GAP: missing-test] Paying an already-paid order returns 400."""
        # Create and pay an order first
        client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
        order_resp = client.post("/api/v1/orders", headers=auth_headers)
        order_id = order_resp.get_json()["data"]["id"]
        client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)

        # Admin tries to pay the already-paid order
        resp = client.post(f"/api/v1/admin/orders/{order_id}/pay", headers=admin_headers)
        assert resp.status_code == 400
        assert "Cannot" in resp.get_json()["message"]

    def test_toggle_product_active_unauthorized(self, client, auth_headers):
        """[GAP: missing-test] Toggle product active without admin returns 403."""
        resp = client.put("/api/v1/admin/products/1/toggle-active",
                          headers=auth_headers)
        assert resp.status_code == 403

    def test_adjust_balance_negative_balance(self, client, admin_headers):
        """[GAP: missing-test] Adjust balance causing negative balance returns 400."""
        # customer@shopminer.com has balance=500000
        # -500001 makes it negative
        resp = client.put("/api/v1/admin/users/2/balance", headers=admin_headers, json={
            "amount": -500001,
        })
        assert resp.status_code == 400
        assert "negative" in resp.get_json()["message"]

    def test_adjust_balance_unauthorized(self, client, auth_headers):
        """[GAP: missing-test] Adjust balance without admin returns 403."""
        resp = client.put("/api/v1/admin/users/2/balance", headers=auth_headers, json={
            "amount": 1000,
        })
        assert resp.status_code == 403

    def test_get_admin_product_unauthorized(self, client, auth_headers):
        """[GAP: missing-test] Get product detail without admin returns 403."""
        resp = client.get("/api/v1/admin/products/1", headers=auth_headers)
        assert resp.status_code == 403

    def test_create_product_unauthorized(self, client, auth_headers):
        """[GAP: missing-test] Create product without admin returns 403."""
        resp = client.post("/api/v1/admin/products", headers=auth_headers, json={
            "name": "Should Fail", "price": 1000, "stock": 1,
        })
        assert resp.status_code == 403

    def test_update_product_unauthorized(self, client, auth_headers):
        """[GAP: missing-test] Update product without admin returns 403."""
        resp = client.put("/api/v1/admin/products/1", headers=auth_headers, json={
            "name": "Should Fail",
        })
        assert resp.status_code == 403

    def test_admin_reset_all_mode_clears_test_orders(self, client, admin_headers, app):
        """[GAP: missing-test] Admin reset all mode removes test user orders."""
        # Create a "test" user (email not ending with @shopminer.uci
        # and not admin/customer@shopminer.com)
        from app.models.user import User
        from app.models.order import Order, OrderItem, OrderStatusLog
        from app.models.product import Product
        with app.app_context():
            test_user = User(
                first_name="Reset", last_name="Test",
                email="reset_test_user@example.com",
                address="addr",
            )
            test_user.set_password("Test1234")
            db.session.add(test_user)
            db.session.flush()

            product = Product.query.first()
            order = Order(
                user_id=test_user.id, total_amount=1000,
                status=Order.STATUS_PENDING,
                shipping_address="addr", shipping_phone="13800138000",
            )
            db.session.add(order)
            db.session.flush()
            item = OrderItem(order_id=order.id, product_id=product.id,
                             quantity=1, unit_price=1000)
            db.session.add(item)
            OrderStatusLog.create(order.id, None, Order.STATUS_PENDING)
            db.session.commit()
            order_id = order.id

        # Trigger reset all
        resp = client.post("/api/v1/admin/reset", headers=admin_headers,
                           json={"mode": "all"})
        assert resp.status_code == 200

        with app.app_context():
            deleted_order = db.session.get(Order, order_id)
            assert deleted_order is None, "Test order should be deleted"
