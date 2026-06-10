"""Playwright E2E tests for ratings display."""
import pytest


@pytest.mark.order(3)
class TestRatings:
    """Rating display flow."""

    def test_homepage_shows_ratings(self, page, flask_server):
        """Product cards on homepage show rating stars."""
        page.goto("http://127.0.0.1:5000")
        page.wait_for_timeout(2000)
        # Check if product cards show rating stars
        # The el-rate component should be present in product cards
        has_rating = page.locator('.el-rate').first.is_visible()
        has_no_rating = page.locator('text=暂无评价').first.is_visible()
        # Either ratings or "no rating" should be visible on some cards
        assert has_rating or has_no_rating, "No rating display found on homepage"

    def test_product_detail_shows_rating_summary(self, page, flask_server):
        """Product detail page shows rating summary."""
        # Navigate to first product
        page.goto("http://127.0.0.1:5000/#/product/1")
        page.wait_for_timeout(2000)
        # Check for rating section (el-rate) or empty state (暂无评价)
        has_rating_section = (
            page.locator('.el-rate').first.is_visible() or
            page.locator('text=暂无评价').first.is_visible()
        )
        assert has_rating_section, "Rating section not found on product detail page"
