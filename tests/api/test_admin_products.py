"""Tests for admin product management API."""
import json


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
