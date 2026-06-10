"""Regression tests for BUG-003: recharge amount type validation."""


class TestRechargeValidation:
    """POST /api/v1/auth/me/recharge amount validation."""

    def test_recharge_string_amount(self, client, auth_headers):
        """String amount should be rejected with 400."""
        resp = client.post("/api/v1/auth/me/recharge", json={
            "amount": "lots",
        }, headers=auth_headers)
        json = resp.get_json()
        assert resp.status_code == 400
        assert json["code"] == 400

    def test_recharge_negative_amount(self, client, auth_headers):
        """Negative amount should be rejected with 400."""
        resp = client.post("/api/v1/auth/me/recharge", json={
            "amount": -100,
        }, headers=auth_headers)
        json = resp.get_json()
        assert resp.status_code == 400
        assert json["code"] == 400

    def test_recharge_zero_amount(self, client, auth_headers):
        """Zero amount should be rejected with 400."""
        resp = client.post("/api/v1/auth/me/recharge", json={
            "amount": 0,
        }, headers=auth_headers)
        json = resp.get_json()
        assert resp.status_code == 400
        assert json["code"] == 400

    def test_recharge_huge_amount(self, client, auth_headers):
        """Amount exceeding max (10000000) should be rejected with 400."""
        resp = client.post("/api/v1/auth/me/recharge", json={
            "amount": 99999999,
        }, headers=auth_headers)
        json = resp.get_json()
        assert resp.status_code == 400
        assert json["code"] == 400

    def test_recharge_valid(self, client, auth_headers):
        """Valid amount should return 200 and increase balance."""
        resp = client.post("/api/v1/auth/me/recharge", json={
            "amount": 1000,
        }, headers=auth_headers)
        json = resp.get_json()
        assert resp.status_code == 200
        assert json["code"] == 200
        assert json["data"]["balance"] == 501000  # 500000 + 1000
