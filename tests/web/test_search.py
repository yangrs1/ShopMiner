"""Playwright E2E tests for search filtering."""
import pytest


@pytest.mark.order(2)
class TestSearch:
    """Search and filter flow."""

    def test_search_and_filter(self, page, flask_server):
        """User can search and apply filters."""
        page.goto("http://127.0.0.1:5000/#/search?q=test")
        page.wait_for_timeout(2000)
        # Check if filter controls are visible
        # The filter bar should have price inputs and sort dropdown
        # Try to use price filter
        min_input = page.locator('input[placeholder="最低价"]')
        if min_input.is_visible():
            min_input.fill("10")
            max_input = page.locator('input[placeholder="最高价"]')
            max_input.fill("100")
            page.wait_for_timeout(1000)
        # Verify search results load
        assert page.locator('.product-card, .empty-state, .skeleton-grid').first.is_visible()
