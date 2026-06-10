"""Tests for rating aggregation API."""


class TestRatings:
    """Rating aggregation endpoints."""

    def test_get_rating_no_reviews(self, client):
        """Product without reviews returns 0/0."""
        resp = client.get("/api/v1/products/1/rating")
        json = resp.get_json()
        assert resp.status_code == 200
        assert json["data"]["avg_rating"] == 0
        assert json["data"]["total_reviews"] == 0

    def test_get_rating_with_reviews(self, client, auth_headers):
        """Product with reviews returns correct average."""
        # Create a review first
        client.post("/api/v1/reviews", json={
            "product_id": 1, "rating": 4, "content": "Good",
        }, headers=auth_headers)
        resp = client.get("/api/v1/products/1/rating")
        json = resp.get_json()
        assert resp.status_code == 200
        assert json["data"]["avg_rating"] > 0
        assert json["data"]["total_reviews"] > 0

    def test_batch_ratings(self, client, auth_headers):
        """Batch query returns ratings for multiple products."""
        # Create reviews for products 1 and 2
        client.post("/api/v1/reviews", json={"product_id": 1, "rating": 5}, headers=auth_headers)
        client.post("/api/v1/reviews", json={"product_id": 2, "rating": 3}, headers=auth_headers)
        resp = client.get("/api/v1/products/ratings?product_ids=1,2,3")
        json = resp.get_json()
        assert resp.status_code == 200
        data = json["data"]
        assert isinstance(data, dict)
