"""Playwright E2E tests for admin product management."""
import pytest


@pytest.mark.order(1)
class TestAdminProducts:
    """Admin product management flow."""

    def test_admin_login_and_view_products(self, page, flask_server):
        """Admin can log in and navigate to product management."""
        page.goto("http://127.0.0.1:5000")
        # Navigate to login
        page.goto("http://127.0.0.1:5000/#/login")
        page.fill('input[placeholder*="邮箱"]', "admin@shopminer.com")
        page.fill('input[placeholder*="密码"]', "Admin@123")
        page.click('button:has-text("登录")')
        page.wait_for_timeout(1000)
        # Navigate to admin
        page.goto("http://127.0.0.1:5000/#/admin")
        page.wait_for_timeout(1000)
        # Click products tab
        page.click('text=商品管理')
        page.wait_for_timeout(1000)
        # Verify product management UI loaded
        assert page.is_visible('text=新增商品')
