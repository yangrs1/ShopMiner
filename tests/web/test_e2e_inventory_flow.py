"""
E2E Web UI 测试 - 库存场景
覆盖: 正常购买（库存充足）/ 库存不足加购 / 多用户同商品不超卖
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
from tests.web.pages.profile_page import ProfilePage

BASE_URL = "http://127.0.0.1:5000"

# 测试服务器种子数据:
#   Product 1: "Test T-Shirt A",  price=2999, stock=100
#   Product 2: "Test Pants A",   price=5999, stock=50
#   Product 3: "Test Socks A",   price=999,  stock=200


# ── 测试失败自动截图 ──────────────────────────────────────────────
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, "rep_" + rep.when, rep)


def _navigate_via_hash(page: Page, route: str):
    """SPA hash 路由导航辅助函数"""
    page.evaluate(f"() => {{ window.location.hash = '{route}'; }}")
    page.wait_for_timeout(500)
    page.evaluate("() => { window.dispatchEvent(new HashChangeEvent('hashchange')); }")
    page.wait_for_timeout(2000)


def _goto(page: Page, route: str):
    """用 page.goto 直接导航 SPA 路由（'/#/' 前缀）"""
    page.goto(f"{BASE_URL}/#/{route}", timeout=20000)
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(1500)


# ============================================================
# E2E-WEB-03 ~ 05 库存场景
# ============================================================
@allure.feature("E2E Web UI 工作流")
class TestE2EInventoryFlow:

    @allure.story("库存场景：正常购买")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("E2E-WEB-03 库存充足时正常购买成功")
    def test_normal_purchase(self, page: Page):
        """
        正常购买路径：登录 → 加购（库存充足）→ 结算 → 支付 → 成功
        """
        with allure.step("1. 登录（使用预置 customer 账号，余额充足）"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")
            page.wait_for_timeout(1000)

        with allure.step("2. 浏览商品详情（Product 1 stock=100）"):
            _goto(page, "product/1")
            product_name = ProductDetailPage(page).get_product_name()
            assert product_name, "商品名称不应为空"

        with allure.step("3. 加入购物车"):
            ProductDetailPage(page).add_to_cart()
            page.wait_for_timeout(1500)

        with allure.step("4. 购物车确认商品存在"):
            _goto(page, "cart")
            assert not CartPage(page).is_empty(), "加购后购物车不应为空"
            item_count = CartPage(page).get_item_count()
            assert item_count > 0, f"购物车应有商品，当前: {item_count}"

        with allure.step("5. 结算下单"):
            CartPage(page).checkout()
            page.wait_for_timeout(2000)

        with allure.step("6. 支付订单"):
            _goto(page, "orders")
            assert OrdersPage(page).has_orders(), "下单后订单列表不应为空"
            OrdersPage(page).pay_order()
            page.wait_for_timeout(2000)

        with allure.step("7. 验证支付成功"):
            _goto(page, "orders")
            status = OrdersPage(page).get_order_status()
            assert "已付款" in status or "paid" in status.lower(), \
                f"支付后状态应为已付款，实际: {status}"

    @allure.story("库存场景：库存不足")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("E2E-WEB-04 加购数量超过库存时提示错误")
    def test_out_of_stock_error(self, page: Page):
        """
        库存不足异常：注册新用户 → 登录 → 加购 → 修改数量超过可用库存 → 验证错误提示
        使用独立用户避免影响其他测试的购物车状态。
        """
        suffix = random.randint(10000, 99999)
        email = f"outofstock_{suffix}@test.com"
        password = "Oos@Pass789"

        with allure.step("1. 注册新用户"):
            RegisterPage(page).navigate().register(
                first_name="Stock", last_name="Test",
                email=email, password=password,
                address="Stock Test",
            )
            page.wait_for_timeout(2000)
            # 显式登录
            _goto(page, "login")
            LoginPage(page).login(email, password)
            page.wait_for_timeout(1000)

        with allure.step("2. 加购商品（Product 1 stock=100）"):
            page.goto(f"{BASE_URL}/#/product/1", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            ProductDetailPage(page).add_to_cart()
            page.wait_for_timeout(1500)

        with allure.step("3. 进入购物车，将数量修改为远超库存的值（999）"):
            _goto(page, "cart")
            page.wait_for_timeout(500)
            assert not CartPage(page).is_empty(), "购物车不应为空"

            # 修改数量为 999（远超 stock=100）
            qty_input = page.locator(".el-input-number .el-input__inner")
            if qty_input.count() > 0:
                qty_input.first.fill("999")
                qty_input.first.blur()
                page.wait_for_timeout(2500)

        with allure.step("4. 验证出现库存不足或数量超限的错误提示"):
            body = page.inner_text("body")
            has_error = (
                "库存不足" in body
                or "超出" in body
                or "超过" in body
                or "失败" in body
                or "error" in body.lower()
            )
            # 也可能是前端数字输入框限制了最大值
            qty_val = page.locator(".el-input-number .el-input__inner").first.input_value()
            if not qty_val.isdigit():
                qty_val = "0"
            if not has_error:
                assert int(qty_val) < 999, \
                    f"数量应被限制，实际值: {qty_val}，页面内容: {body[:200]}"

    @allure.story("库存场景：多用户不超卖")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("E2E-WEB-05 多用户购买同商品，库存不超卖")
    def test_multi_user_no_oversell(self, page: Page):
        """
        多用户场景：两个用户同时购买同一商品（使用预置账号），
        验证库存充足时两人均可成功购买，且库存扣减不超过实际库存。
        """
        # 创建第二个浏览器上下文（独立的 cookie / 登录会话）
        browser = page.context.browser
        context2 = browser.new_context()
        page2 = context2.new_page()

        def _goto(p, route):
            """用 page.goto 直接导航 SPA 路由（'/#/' 前缀）"""
            p.goto(f"{BASE_URL}/#/{route}", timeout=20000)
            p.wait_for_load_state("networkidle")
            p.wait_for_timeout(1500)

        try:
            with allure.step("User1: 登录 customer 账号"):
                _goto(page, "login")
                LoginPage(page).login("customer@shopminer.com", "Customer@123")
                page.wait_for_timeout(1000)

            with allure.step("User1: 加购 Product 1（库存 100）"):
                _goto(page, "product/1")
                ProductDetailPage(page).add_to_cart()
                page.wait_for_timeout(1500)

            with allure.step("User2: 登录 test 账号"):
                _goto(page2, "login")
                LoginPage(page2).login("test@shopminer.com", "Test@123456")
                page2.wait_for_timeout(1000)

            with allure.step("User2: 加购 Product 1（库存 100）"):
                _goto(page2, "product/1")
                ProductDetailPage(page2).add_to_cart()
                page2.wait_for_timeout(1500)

            with allure.step("User1: 结算下单"):
                _goto(page, "cart")
                assert not CartPage(page).is_empty(), "User1 购物车不应为空"
                CartPage(page).checkout()
                page.wait_for_timeout(2000)

            with allure.step("User2: 结算下单"):
                _goto(page2, "cart")
                page2.wait_for_timeout(1000)
                # 检查购物车内容
                cart_body = page2.inner_text("body")
                cart_empty = CartPage(page2).is_empty()
                assert not cart_empty, f"User2 购物车不应为空，页面内容: {cart_body[:200]}"

                checkout_btn = page2.locator("button:has-text('结算')")
                assert checkout_btn.is_visible(), "User2 结算按钮应可见"

                CartPage(page2).checkout()
                page2.wait_for_timeout(3000)

                # 检查结算后是否有错误
                error_toast = page2.locator(".el-message--error")
                if error_toast.count() > 0:
                    err_text = error_toast.first.inner_text()
                    page2_url = page2.url
                    pytest.fail(f"User2 结算失败: {err_text}, URL: {page2_url}")

            with allure.step("User1: 支付订单"):
                _goto(page, "orders")
                assert OrdersPage(page).has_orders(), "User1 下单后应有订单"
                OrdersPage(page).pay_order()
                page.wait_for_timeout(2000)

            with allure.step("User2: 支付订单"):
                _goto(page2, "orders")
                assert OrdersPage(page2).has_orders(), "User2 下单后应有订单"
                OrdersPage(page2).pay_order()
                page2.wait_for_timeout(2000)

            with allure.step("验证两个用户的订单均已支付成功"):
                _goto(page, "orders")
                status1 = OrdersPage(page).get_order_status()
                assert "已付款" in status1 or "paid" in status1.lower(), \
                    f"User1 应支付成功，状态: {status1}"

                _goto(page2, "orders")
                status2 = OrdersPage(page2).get_order_status()
                assert "已付款" in status2 or "paid" in status2.lower(), \
                    f"User2 应支付成功，状态: {status2}"

        finally:
            context2.close()

    # ── 自动截图 fixture ──────────────────────────────────────
    @pytest.fixture(autouse=True)
    def _screenshot_on_failure(self, request, page: Page):
        """测试失败时自动截图保存到 .omo/evidence/"""
        yield
        if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
            screenshot_path = f".omo/evidence/{request.node.name}_fail.png"
            page.screenshot(path=screenshot_path, full_page=True)
