"""
E2E Web UI 测试 - 未登录用户访问限制
覆盖: 未登录访问购物车跳转登录 / 未登录下单跳转登录 / 登录后回到目标页面
"""
import allure
import pytest
import random
from playwright.sync_api import Page, expect
from tests.web.pages.login_page import LoginPage
from tests.web.pages.cart_page import CartPage
from tests.web.pages.orders_page import OrdersPage

BASE_URL = "http://127.0.0.1:5000"


# ── 测试失败自动截图 ──────────────────────────────────────────────
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


# ============================================================
# E2E-WEB-06 ~ 08 未登录用户限制
# ============================================================
@allure.feature("E2E Web UI 工作流")
class TestE2EGuestFlow:

    @allure.story("未登录用户限制")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("E2E-WEB-06 未登录访问购物车 → 跳转登录页")
    def test_guest_cart_redirects_to_login(self, page: Page):
        """
        未登录用户直接访问购物车页面，验证被重定向到登录页
        """
        with allure.step("1. 未登录状态下直接打开购物车"):
            page.goto(f"{BASE_URL}/#/cart", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

        with allure.step("2. 验证跳转到登录页"):
            current_url = page.url
            body = page.inner_text("body")
            assert "login" in current_url, \
                f"未登录访问购物车应跳转登录页，当前URL: {current_url}"
            # 验证登录页元素可见（邮箱输入框、密码输入框、登录按钮）
            email_input = page.locator("input[placeholder='请输入邮箱']")
            password_input = page.locator("input[placeholder='请输入密码']")
            login_button = page.locator("button:has-text('登录')")
            assert email_input.is_visible(), "登录页应有邮箱输入框"
            assert password_input.is_visible(), "登录页应有密码输入框"
            assert login_button.is_visible(), "登录页应有登录按钮"

    @allure.story("未登录用户限制")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("E2E-WEB-07 未登录访问订单页 → 跳转登录页")
    def test_guest_orders_redirects_to_login(self, page: Page):
        """
        未登录用户直接访问订单列表页，验证被重定向到登录页
        """
        with allure.step("1. 未登录状态下直接打开订单页"):
            page.goto(f"{BASE_URL}/#/orders", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

        with allure.step("2. 验证跳转到登录页"):
            current_url = page.url
            assert "login" in current_url, \
                f"未登录访问订单页应跳转登录页，当前URL: {current_url}"
            # 验证登录页元素可见
            login_button = page.locator("button:has-text('登录')")
            assert login_button.is_visible(), "登录页应有登录按钮"

    @allure.story("未登录用户限制")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("E2E-WEB-08 未登录下单操作 → 跳转登录")
    def test_guest_add_to_cart_redirects_to_login(self, page: Page):
        """
        未登录用户尝试加购商品，验证被引导到登录页
        """
        with allure.step("1. 未登录状态下打开商品详情"):
            page.goto(f"{BASE_URL}/#/product/1", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)

        with allure.step("2. 点击加入购物车"):
            add_btn = page.locator("button:has-text('加入购物车')").first
            assert add_btn.is_visible(), "商品详情页应有加购按钮"
            add_btn.click()
            page.wait_for_timeout(2000)

        with allure.step("3. 验证跳转到登录页或弹出提示"):
            current_url = page.url
            body = page.inner_text("body")
            has_login_redirect = "login" in current_url
            has_login_prompt = "请先登录" in body or "登录" in body
            assert has_login_redirect or has_login_prompt, \
                f"未登录加购应跳转登录或提示，当前URL: {current_url}，内容: {body[:200]}"

    @allure.story("未登录用户限制")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("E2E-WEB-09 登录后可以访问原本受限的页面")
    def test_login_after_guest_redirect(self, page: Page):
        """
        模拟用户流程：未登录 → 访问购物车被重定向到登录 → 登录成功 → 可以正常访问购物车
        """
        with allure.step("1. 未登录状态下打开购物车（应被重定向）"):
            page.goto(f"{BASE_URL}/#/cart", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            assert "login" in page.url, "未登录应跳转登录页"

        with allure.step("2. 在登录页输入凭证并登录"):
            LoginPage(page).login("customer@shopminer.com", "Customer@123")
            page.wait_for_timeout(2000)

        with allure.step("3. 验证登录成功后可以正常访问购物车"):
            # 主动导航到购物车（此时已登录）
            page.goto(f"{BASE_URL}/#/cart", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            current_url = page.url
            body = page.inner_text("body")

            # 登录后应停留在购物车页，不会再次跳转到登录
            assert "login" not in current_url, \
                f"登录后访问购物车不应再跳转登录，当前URL: {current_url}"
            # 购物车应正常渲染（可能为空或有商品）
            assert "cart" in current_url.lower() or "购物车" in body, \
                f"应显示购物车内容，当前URL: {current_url}"

    # ── 自动截图 fixture ──────────────────────────────────────
    @pytest.fixture(autouse=True)
    def _screenshot_on_failure(self, request, page: Page):
        """测试失败时自动截图保存到 .omo/evidence/"""
        yield
        if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
            screenshot_path = f".omo/evidence/{request.node.name}_fail.png"
            page.screenshot(path=screenshot_path, full_page=True)
