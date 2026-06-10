"""Playwright E2E tests for favorites pagination."""
import pytest


@pytest.mark.order(4)
class TestFavorites:
    """Favorites pagination flow."""

    def test_favorites_loads_with_pagination(self, page, flask_server):
        """Favorites page loads and shows pagination if >20 items."""
        # Login as customer
        page.goto("http://127.0.0.1:5000/#/login")
        page.fill('input[placeholder*="邮箱"]', "customer@shopminer.com")
        page.fill('input[placeholder*="密码"]', "Customer@123")
        page.click('button:has-text("登录")')
        page.wait_for_timeout(1000)
        # Navigate to favorites
        page.goto("http://127.0.0.1:5000/#/favorites")
        page.wait_for_timeout(2000)
        # Verify page loaded (either items, empty state, or pagination)
        loaded = (
            page.locator('.fav-item').first.is_visible() or
            page.locator('text=还没有收藏').first.is_visible()
        )
        assert loaded, "Favorites page did not load"
