"""Regression tests for cart bug fixes.

BUG-002: DELETE /api/v1/cart/<product_id> returns 404 for non-existent item
BUG-004: PUT /api/v1/cart/<product_id> validates quantity is required and positive
"""

import pytest


class TestRemoveCartItemNonExistent:
    """BUG-002: DELETE returns 200 for non-existent cart item."""

    def test_remove_nonexistent_cart_item(self, client, auth_headers):
        """Deleting a cart item that was never added should return 404."""
        resp = client.delete("/api/v1/cart/99999", headers=auth_headers)
        assert resp.status_code == 404
        data = resp.get_json()
        assert data["code"] == 404
        assert data["message"] == "Cart item not found"


class TestUpdateCartItemValidation:
    """BUG-004: PUT silently defaults quantity=1 when field is missing."""

    def test_update_cart_missing_quantity(self, client, auth_headers):
        """PUT without quantity field should return 400."""
        # First add an item
        client.post("/api/v1/cart", headers=auth_headers, json={
            "product_id": 1, "quantity": 1,
        })
        # Update without quantity field
        resp = client.put("/api/v1/cart/1", headers=auth_headers, json={})
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["code"] == 400
        assert data["message"] == "Quantity is required"

    def test_update_cart_invalid_quantity(self, client, auth_headers):
        """PUT with non-integer quantity should return 400."""
        client.post("/api/v1/cart", headers=auth_headers, json={
            "product_id": 1, "quantity": 1,
        })
        resp = client.put("/api/v1/cart/1", headers=auth_headers, json={
            "quantity": "abc",
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["code"] == 400
        assert data["message"] == "Quantity must be a positive integer"

    def test_update_cart_valid_quantity(self, client, auth_headers):
        """PUT with valid quantity should succeed (happy path)."""
        client.post("/api/v1/cart", headers=auth_headers, json={
            "product_id": 1, "quantity": 1,
        })
        resp = client.put("/api/v1/cart/1", headers=auth_headers, json={
            "quantity": 3,
        })
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["code"] == 200
        assert data["message"] == "Quantity updated"
        # Verify the quantity was actually updated
        items = data["data"]
        item = next(i for i in items if i.get("id") == 1)
        assert item["quantity"] == 3
