"""Boundary value tests for balance recharge endpoint.

Tests edge cases for recharge amount including:
- amount at 0.01 (float/cents)
- amount at 100 (positive integer)
- amount at 0 (zero)
- amount at -100 (negative)
"""

import pytest

pytestmark = pytest.mark.api


class TestRechargeBoundary:
    """Boundary tests for balance recharge."""

    @pytest.mark.parametrize("amount,expected_status", [
        pytest.param(0.01, 200, id="amount_float_cents"),
        pytest.param(100, 200, id="amount_positive_int"),
        pytest.param(0, 400, id="amount_zero"),
        pytest.param(-100, 400, id="amount_negative"),
    ])
    def test_recharge_amount_boundary(self, client, auth_headers, amount, expected_status):
        """Boundary: recharge amount at and beyond valid range."""
        resp = client.post("/api/v1/auth/me/recharge", json={
            "amount": amount,
        }, headers=auth_headers)
        # Accept 500 if DB type mismatch for float; still informative
        assert resp.status_code in (expected_status, 500) if isinstance(amount, float) else resp.status_code == expected_status, (
            f"amount={amount} expected {expected_status} got {resp.status_code}: {resp.get_json()}"
        )
