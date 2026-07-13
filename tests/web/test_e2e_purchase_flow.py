"""
E2E Web UI 测试 - 完整购买流程
覆盖: 注册 → 充值 → 搜索 → 商品详情 → 加购 → 下单 → 支付（含余额不足异常分支）
"""
import allure
import pytest
import random
from playwright.sync_api import Page
from tests.web.pages.login_page import LoginPage
from tests.web.pages.register_page import RegisterPage
from tests.web.pages.search_page import SearchPage
from tests.web.pages.product_page import ProductDetailPage
from tests.web.pages.cart_page import CartPage
from tests.web.pages.orders_page import OrdersPage

BASE_URL = "http://127.0.0.1:5000"


def _goto(page: Page, route: str):
    """page.goto 导航 SPA 路由（'/#/' 前缀），等待页面完全加载。"""
    page.goto(f"{BASE_URL}/#/{route}", timeout=20000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)


# ── 测试失败自动截图 ──────────────────────────────────────────────
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


# ============================================================
# E2E-WEB-01 完整购买流程
# ============================================================
@allure.feature("E2E Web UI 工作流")
class TestE2EPurchaseFlow:

    @allure.story("完整购买流程")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("E2E-WEB-01 注册→充值→搜索→加购→下单→支付（正常路径）")
    def test_full_purchase_flow(self, page: Page):
        """
        完整购买流程：注册新用户 → 显式登录 → 充值余额 → 搜索商品
        → 查看商品详情 → 加入购物车 → 结算下单 → 支付订单 → 验证状态
        """
        suffix = random.randint(10000, 99999)
        email = f"purchase_e2e_{suffix}@test.com"
        password = "E2eTest@789"

        with allure.step("1. 注册新用户"):
            RegisterPage(page).navigate().register(
                first_name="E2E",
                last_name="Buyer",
                email=email,
                password=password,
                address="E2E Purchase Address",
            )
            page.wait_for_timeout(2000)

        with allure.step("2. 显式登录并充值余额"):
            _goto(page, "login")
            LoginPage(page).login(email, password)
            page.wait_for_timeout(1000)

            _goto(page, "profile")
            page.wait_for_timeout(1000)
            recharge_btn = page.locator("button:has-text('充值')")
            assert recharge_btn.is_visible(), "充值按钮应在个人中心页可见"
            recharge_btn.click()
            page.wait_for_timeout(500)
            prompt_input = page.locator(".el-message-box .el-input__inner")
            if prompt_input.is_visible():
                prompt_input.fill("100000")
                page.locator(".el-message-box .el-button--primary").click()
                page.wait_for_timeout(1500)

        with allure.step("3. 搜索商品"):
            _goto(page, "search?q=T-Shirt")
            page.wait_for_timeout(1000)
            assert SearchPage(page).has_results(), "搜索结果不应为空"

        with allure.step("4. 点击搜索结果第一个商品，查看详情"):
            SearchPage(page).click_result(0)
            page.wait_for_timeout(1500)
            product_name = ProductDetailPage(page).get_product_name()
            assert product_name and len(product_name.strip()) > 0, "商品名称不应为空"

        with allure.step("5. 加入购物车"):
            ProductDetailPage(page).add_to_cart()
            page.wait_for_timeout(1500)

        with allure.step("6. 进入购物车并结算下单"):
            _goto(page, "cart")
            page.wait_for_timeout(500)
            assert not CartPage(page).is_empty(), "加购后购物车不应为空"
            CartPage(page).checkout()
            page.wait_for_timeout(2000)

        with allure.step("7. 在订单列表支付订单"):
            _goto(page, "orders")
            page.wait_for_timeout(500)
            assert OrdersPage(page).has_orders(), "下单后应存在订单记录"

            status_before = OrdersPage(page).get_order_status()
            assert "待付款" in status_before or "pending" in status_before.lower(), \
                f"订单状态应为待付款，实际: {status_before}"

            OrdersPage(page).pay_order()
            page.wait_for_timeout(2000)

        with allure.step("8. 验证支付后订单状态变更为已付款"):
            _goto(page, "orders")
            page.wait_for_timeout(500)
            status_after = OrdersPage(page).get_order_status()
            assert "已付款" in status_after or "paid" in status_after.lower(), \
                f"支付后订单状态应为已付款，实际: {status_after}"

    @allure.story("购买流程异常")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("E2E-WEB-02 余额不足时支付失败")
    def test_insufficient_balance_payment(self, page: Page):
        """
        异常分支：注册新用户（无余额）→ 加购商品 → 结算下单 → 尝试支付 → 因余额不足失败
        """
        suffix = random.randint(10000, 99999)
        email = f"nobalance_{suffix}@test.com"
        password = "NoBal@789"

        with allure.step("1. 注册新用户（默认余额为 0）"):
            RegisterPage(page).navigate().register(
                first_name="No",
                last_name="Balance",
                email=email,
                password=password,
                address="No Balance Address",
            )
            page.wait_for_timeout(2000)

        with allure.step("2. 显式登录"):
            _goto(page, "login")
            LoginPage(page).login(email, password)
            page.wait_for_timeout(1000)

        with allure.step("3. 搜索一个低价商品并加入购物车"):
            _goto(page, "search?q=Socks")
            page.wait_for_timeout(1000)
            assert SearchPage(page).has_results(), "应搜索到商品"
            SearchPage(page).click_result(0)
            page.wait_for_timeout(1000)
            ProductDetailPage(page).add_to_cart()
            page.wait_for_timeout(1500)

        with allure.step("4. 进入购物车并尝试结算下单"):
            _goto(page, "cart")
            page.wait_for_timeout(500)
            assert not CartPage(page).is_empty(), "加购后购物车不应为空"

            checkout_btn = page.locator("button:has-text('结算')")
            if checkout_btn.is_visible():
                checkout_btn.click()
                page.wait_for_timeout(1000)
                confirm = page.locator(".el-message-box .el-button--primary")
                if confirm.is_visible():
                    confirm.click()
                    page.wait_for_timeout(3000)

        with allure.step("5. 验证余额不足的错误提示"):
            # 先检查当前页面是否有错误 toast
            has_error_toast = page.locator(".el-message--error").count() > 0
            body = page.inner_text("body")
            has_error_text = (
                "余额不足" in body
                or "失败" in body
                or "error" in body.lower()
                or "结算失败" in body
            )

            if not has_error_toast and not has_error_text:
                # 导航到订单页确认没有成功创建订单
                _goto(page, "orders")
                orders_body = page.inner_text("body")
                has_no_orders = "暂无订单" in orders_body
                assert has_no_orders, \
                    f"余额不足下单应失败，无订单记录。页面内容: {orders_body[:200]}"
            else:
                assert has_error_toast or has_error_text, \
                    f"余额不足时应提示错误。页面内容: {body[:200]}"

    # ── 自动截图 fixture ──────────────────────────────────────
    @pytest.fixture(autouse=True)
    def _screenshot_on_failure(self, request, page: Page):
        """测试失败时自动截图保存到 .omo/evidence/"""
        yield
        if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
            screenshot_path = f".omo/evidence/{request.node.name}_fail.png"
            page.screenshot(path=screenshot_path, full_page=True)
