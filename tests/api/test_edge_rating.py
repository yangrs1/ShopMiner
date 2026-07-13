"""Boundary value tests for review rating validation.

Tests edge cases for review rating values including:
- rating at 0 (below valid range)
- rating at 6 (above valid range)
- rating at 1 (minimum valid)
- rating at 5 (maximum valid)
"""

import pytest

pytestmark = pytest.mark.api


class TestRatingBoundary:
    """Boundary tests for review rating validation."""

    @pytest.mark.parametrize("rating,expected_status", [
        pytest.param(0, 400, id="rating_zero"),
        pytest.param(6, 400, id="rating_above_max"),
        pytest.param(1, 201, id="rating_min_valid"),
        pytest.param(5, 201, id="rating_max_valid"),
    ])
    def test_review_rating_boundary(self, client, auth_headers, rating, expected_status):
        """Boundary: rating values at and beyond valid range 1-5."""
        resp = client.post("/api/v1/reviews", json={
            "product_id": 1,
            "rating": rating,
            "content": "Boundary test review",
        }, headers=auth_headers)
        assert resp.status_code == expected_status, (
            f"rating={rating} expected {expected_status} got {resp.status_code}: {resp.get_json()}"
        )
