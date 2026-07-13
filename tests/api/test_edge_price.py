"""Boundary value tests for product price search filters.

Tests edge cases for min_price, max_price, sort_by including:
- min_price at zero, negative, and huge values
- Inverted price range (min_price > max_price)
- Invalid sort_by parameter
"""

import pytest

pytestmark = pytest.mark.api


class TestProductPriceBoundary:
    """Boundary tests for product price search filters."""

    @pytest.mark.parametrize("min_price,expected_status", [
        pytest.param(0, 200, id="zero_price"),
        pytest.param(-1, 400, id="negative_price"),
        pytest.param(999999999, 200, id="huge_price"),
    ])
    def test_min_price_boundary(self, client, min_price, expected_status):
        """Boundary: min_price at and beyond valid range."""
        resp = client.get(f"/api/v1/products?min_price={min_price}")
        assert resp.status_code == expected_status, (
            f"min_price={min_price} expected {expected_status} got {resp.status_code}"
        )

    def test_min_price_greater_than_max_price(self, client):
        """Boundary: inverted price range returns 400."""
        resp = client.get("/api/v1/products?min_price=5000&max_price=1000")
        assert resp.status_code == 400

    def test_invalid_sort_by(self, client):
        """Boundary: invalid sort_by returns 400."""
        resp = client.get("/api/v1/products?sort_by=invalid")
        assert resp.status_code == 400
