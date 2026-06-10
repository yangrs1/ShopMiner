"""Tests for product search sorting and filtering."""


class TestSearch:
    """Product search/filter/sort endpoints."""

    def test_default_search(self, client):
        """Default search returns products sorted by created_at desc."""
        resp = client.get("/api/v1/products")
        json = resp.get_json()
        assert resp.status_code == 200
        assert len(json["data"]["products"]) > 0

    def test_price_filter(self, client):
        """Filter by price range returns only matching products."""
        resp = client.get("/api/v1/products?min_price=1000&max_price=5000")
        json = resp.get_json()
        assert resp.status_code == 200
        for p in json["data"]["products"]:
            assert 1000 <= p["price"] <= 5000

    def test_sort_by_price_asc(self, client):
        """Sort by price ascending."""
        resp = client.get("/api/v1/products?sort_by=price&order=asc")
        json = resp.get_json()
        assert resp.status_code == 200
        prices = [p["price"] for p in json["data"]["products"]]
        assert prices == sorted(prices)

    def test_sort_by_price_desc(self, client):
        """Sort by price descending."""
        resp = client.get("/api/v1/products?sort_by=price&order=desc")
        json = resp.get_json()
        assert resp.status_code == 200
        prices = [p["price"] for p in json["data"]["products"]]
        assert prices == sorted(prices, reverse=True)

    def test_invalid_sort_by(self, client):
        """Invalid sort_by returns 400."""
        resp = client.get("/api/v1/products?sort_by=invalid")
        assert resp.status_code == 400

    def test_invalid_order(self, client):
        """Invalid order returns 400."""
        resp = client.get("/api/v1/products?sort_by=price&order=invalid")
        assert resp.status_code == 400

    def test_invalid_price_range(self, client):
        """min_price > max_price returns 400."""
        resp = client.get("/api/v1/products?min_price=5000&max_price=1000")
        assert resp.status_code == 400

    def test_combined_filters(self, client):
        """Multiple filters work together."""
        resp = client.get("/api/v1/products?category=&min_price=1000&sort_by=price&order=asc")
        assert resp.status_code == 200
