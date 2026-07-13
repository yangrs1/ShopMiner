"""Boundary value tests for pagination parameters.

Tests edge cases for page and per_page parameters including:
- page at zero and negative values
- per_page at zero and large values
"""

import pytest

pytestmark = pytest.mark.api


class TestPaginationBoundary:
    """Boundary tests for pagination parameters."""

    @pytest.mark.parametrize("page,expected_status", [
        pytest.param(0, 200, id="page_zero"),
        pytest.param(-1, 200, id="page_negative"),
    ])
    def test_page_boundary(self, client, page, expected_status):
        """Boundary: page at and below valid range."""
        resp = client.get(f"/api/v1/products?page={page}")
        assert resp.status_code == expected_status

    @pytest.mark.parametrize("per_page,expected_status", [
        pytest.param(0, 200, id="per_page_zero"),
        pytest.param(999, 200, id="per_page_large"),
    ])
    def test_per_page_boundary(self, client, per_page, expected_status):
        """Boundary: per_page edge values."""
        resp = client.get(f"/api/v1/products?per_page={per_page}")
        assert resp.status_code == expected_status
