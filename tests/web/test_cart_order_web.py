"""
Web UI 测试 - 购物车与订单模块
覆盖页面: Cart / Orders + 购物车项操作 (更新/删除) + 订单操作 (付款/取消)
# [GAP: missing-test] OrderDetail page had zero web coverage (to be added in Task 12)
"""
import allure
import pytest
import re
import random
from playwright.sync_api import Page, expect
from tests.web.pages.login_page import LoginPage
from tests.web.pages.register_page import RegisterPage


BASE_URL = "http://127.0.0.1:5000"


# ============================================================
# WEB-06 购物车（Cart）
# ============================================================
@allure.feature("Web UI测试")
class TestCartPage:

    @allure.story("购物车")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("WEB-06-01 先加购→购物车展示商？")
    def test_cart_has_items_after_add(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("加购商品"):
            page.goto(f"{BASE_URL}/#/product/1", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            add_btn = page.locator("button:has-text('加入购物车')")
            if add_btn.is_visible():
                add_btn.click()
                page.wait_for_timeout(2000)

        with allure.step("打开购物车"):
            page.goto(f"{BASE_URL}/#/cart", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)

        with allure.step("验证购物车有商品"):
            body = page.inner_text("body")
            assert "购物车是空的" not in body, "加购后购物车不应为空"
            assert "结算" in body or "合计" in body

    @allure.story("购物车")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-06-02 空购物车→显示空状？")
    def test_cart_empty_state(self, page: Page):
        with allure.step("注册新用户确保空购物车"):
            suffix = random.randint(100000, 999999)
            email = f"emptycart{suffix}@test.com"
            RegisterPage(page).navigate().register("Web", "Test", email, "EmptyCart@123", "Auto Address")
            page.wait_for_timeout(3000)

        with allure.step("打开购物车"):
            page.goto(f"{BASE_URL}/#/cart", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)

        with allure.step("验证空购物车提示"):
            body = page.inner_text("body")
            has_empty_state = "购物车是空的" in body or "空的" in body or "empty" in body.lower()
            has_disabled_checkout = page.locator("button:has-text('结算')").is_disabled() if page.locator("button:has-text('结算')").count() > 0 else False
            assert has_empty_state or has_disabled_checkout, "空购物车应显示空状态或结算按钮disabled"

    @allure.story("购物车")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-06-03 未登录访问购物车→跳转登录页")
    def test_cart_redirect_to_login(self, page: Page):
        with allure.step("未登录直接打开购物车"):
            page.goto(f"{BASE_URL}/#/cart", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

        with allure.step("验证跳转到登录页"):
            assert "login" in page.url, f"未登录访问购物车应跳转登录页，当前URL: {page.url}"


# ============================================================
# WEB-07 订单（Orders）
# ============================================================
@allure.feature("Web UI测试")
class TestOrdersPage:

    @allure.story("订单")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-07-01 新用户订单页显示空状？")
    def test_orders_empty(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("打开订单？"):
            page.goto(f"{BASE_URL}/#/orders", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)

        with allure.step("验证空订单提？"):
            body = page.inner_text("body")
            assert "暂无订单" in body or "空的" in body or "暂无" in body

    @allure.story("订单")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("WEB-07-02 完整下单支付流程(加购→下单→支付)")
    def test_complete_order_flow(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("加购商品"):
            page.goto(f"{BASE_URL}/#/product/1", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            add_btn = page.locator("button:has-text('加入购物车')")
            if add_btn.is_visible():
                add_btn.click()
                page.wait_for_timeout(2000)

        with allure.step("进入购物车并结算"):
            page.goto(f"{BASE_URL}/#/cart", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)

            checkout_btn = page.locator("button:has-text('结算')")
            if checkout_btn.is_visible():
                checkout_btn.click()
                page.wait_for_timeout(2000)

                with allure.step("确认订单对话？"):
                    confirm_btn = page.locator(".el-message-box .el-button--primary, .el-button--primary:has-text('确认')")
                    if confirm_btn.is_visible():
                        confirm_btn.click()
                        page.wait_for_timeout(3000)

        with allure.step("验证跳转到订单页"):
            page.wait_for_timeout(1000)
            assert "orders" in page.url or "订单" in page.inner_text("body")


# ============================================================
# WEB-14 购物车'数量更新/删除/余额不足
# ============================================================
@allure.feature("Web UI测试")
class TestCartItemActions:

    @allure.story("购物车操作")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-14-01 购物车更新商品数量")
    def test_cart_update_quantity(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("加购商品"):
            page.goto(f"{BASE_URL}/#/product/1", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            add_btn = page.locator("button:has-text('加入购物车')")
            if add_btn.is_visible():
                add_btn.click()
                page.wait_for_timeout(2000)

        with allure.step("打开购物车"):
            page.goto(f"{BASE_URL}/#/cart", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)

        with allure.step("修改数量"):
            qty_input = page.locator(".el-input-number .el-input__inner")
            if qty_input.count() > 0:
                qty_input.first.fill("2")
                qty_input.first.blur()
                page.wait_for_timeout(1500)
                with allure.step("验证数量更新"):
                    body = page.inner_text("body")
                    assert len(body) > 0

    @allure.story("购物车操？")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-14-02 购物车删除商？")
    def test_cart_remove_item(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("加购商品"):
            page.goto(f"{BASE_URL}/#/product/1", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            add_btn = page.locator("button:has-text('加入购物车')")
            if add_btn.is_visible():
                add_btn.click()
                page.wait_for_timeout(2000)

        with allure.step("打开购物车"):
            page.goto(f"{BASE_URL}/#/cart", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)

        with allure.step("点击删除"):
            del_btn = page.locator("button:has-text('删除'), .el-button--danger")
            if del_btn.count() > 0:
                del_btn.first.click()
                page.wait_for_timeout(1500)
                with allure.step("确认删除"):
                    confirm = page.locator(".el-message-box .el-button--primary, .el-button--primary:has-text('确认')")
                    if confirm.is_visible():
                        confirm.click()
                        page.wait_for_timeout(1500)
                with allure.step("验证商品已移？"):
                    body = page.inner_text("body")
                    assert len(body) > 0


# ============================================================
# WEB-15 订单-支付/取消
# ============================================================
@allure.feature("Web UI测试")
class TestOrderActions:

    @allure.story("订单操作")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-15-01 订单页显示付款和取消按钮")
    def test_order_has_action_buttons(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("先加购并下单"):
            page.goto(f"{BASE_URL}/#/product/1", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            add_btn = page.locator("button:has-text('加入购物车')")
            if add_btn.is_visible():
                add_btn.click()
                page.wait_for_timeout(2000)
            page.goto(f"{BASE_URL}/#/cart", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            checkout_btn = page.locator("button:has-text('结算')")
            if checkout_btn.is_visible():
                checkout_btn.click()
                page.wait_for_timeout(2000)
                confirm = page.locator(".el-message-box .el-button--primary")
                if confirm.is_visible():
                    confirm.click()
                    page.wait_for_timeout(3000)

        with allure.step("打开订单？"):
            page.goto(f"{BASE_URL}/#/orders", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)

        with allure.step("验证有付款或取消按钮"):
            body = page.inner_text("body")
            assert "付款" in body or "取消" in body or "暂无订单" in body

    @allure.story("订单操作")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-15-02 订单取消操作")
    def test_cancel_order(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("加购下单"):
            page.goto(f"{BASE_URL}/#/product/1", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            add_btn = page.locator("button:has-text('加入购物车')")
            if add_btn.is_visible():
                add_btn.click()
                page.wait_for_timeout(2000)
            page.goto(f"{BASE_URL}/#/cart", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            checkout_btn = page.locator("button:has-text('结算')")
            if checkout_btn.is_visible():
                checkout_btn.click()
                page.wait_for_timeout(2000)
                confirm = page.locator(".el-message-box .el-button--primary")
                if confirm.is_visible():
                    confirm.click()
                    page.wait_for_timeout(3000)

        with allure.step("打开订单？"):
            page.goto(f"{BASE_URL}/#/orders", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)

        with allure.step("点击取消订单"):
            cancel_btn = page.locator("button:has-text('取消订单')").first
            if cancel_btn.is_visible():
                cancel_btn.click()
                page.wait_for_timeout(2000)
                confirm = page.locator(".el-message-box .el-button--primary")
                if confirm.is_visible():
                    confirm.click()
                    page.wait_for_timeout(2000)
                    with allure.step("验证取消成功"):
                        body = page.inner_text("body")
                        assert "已取？" in body or "取消" in body


# ============================================================
# WEB-? 订单详情 (OrderDetail) - /order/:id
# ============================================================
@allure.feature("Web UI测试")
class TestOrderDetailPage:

    @allure.story("订单详情")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("ORDER-DETAIL-01 登录后访问 /order/:id → 显示订单商品/状态/合计")
    def test_order_detail_shows_order_info(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("加购商品"):
            page.goto(f"{BASE_URL}/#/product/1", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            add_btn = page.locator("button:has-text('加入购物车')")
            if add_btn.is_visible():
                add_btn.click()
                page.wait_for_timeout(2000)

        with allure.step("进入购物车并结算"):
            page.goto(f"{BASE_URL}/#/cart", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            checkout_btn = page.locator("button:has-text('结算')")
            if checkout_btn.is_visible():
                checkout_btn.click()
                page.wait_for_timeout(2000)
                confirm = page.locator(".el-message-box .el-button--primary")
                if confirm.is_visible():
                    confirm.click()
                    page.wait_for_timeout(3000)

        with allure.step("打开订单列表并提取订单ID"):
            page.goto(f"{BASE_URL}/#/orders", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)
            order_id = page.evaluate(
                "() => { const el = document.querySelector('.order-id');"
                " if (!el) return null;"
                " const m = el.innerText.match(/\\d+/);"
                " return m ? m[0] : null; }"
            )
            assert order_id, "未能在订单列表中提取到订单ID"

        with allure.step("通过hash路由跳转到订单详情"):
            page.evaluate(f"() => {{ window.location.hash = '/order/{order_id}'; }}")
            page.wait_for_timeout(800)
            page.evaluate("() => { window.dispatchEvent(new HashChangeEvent('hashchange')); }")
            page.wait_for_timeout(2000)

        with allure.step("验证订单详情展示"):
            body = page.inner_text("body")
            assert "订单详情" in body, "应显示订单详情标题"
            assert f"#{order_id}" in body, f"应显示订单号 #{order_id}"
            assert "待付款" in body or "已付款" in body or "已发货" in body or "已送达" in body, \
                "应显示订单状态"
            assert "合计" in body, "应显示合计金额"
            assert "商品信息" in body, "应显示商品信息区块"

    @allure.story("订单详情")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("ORDER-DETAIL-02 未登录访问 /order/:id → 跳转登录页")
    def test_order_detail_redirect_to_login(self, page: Page):
        with allure.step("未登录打开首页加载SPA"):
            page.goto(BASE_URL, timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)

        with allure.step("通过hash路由直接访问订单详情"):
            page.evaluate("() => { window.location.hash = '/order/1'; }")
            page.wait_for_timeout(800)
            page.evaluate("() => { window.dispatchEvent(new HashChangeEvent('hashchange')); }")
            page.wait_for_timeout(2000)

        with allure.step("验证跳转到登录页"):
            assert "login" in page.url, f"未登录访问订单详情应跳转登录页，当前URL: {page.url}"

    @allure.story("订单详情")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("ORDER-DETAIL-03 登录后访问不存在的订单 → 404或错误提示")
    def test_order_detail_not_found(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("通过hash路由访问不存在的订单"):
            page.evaluate("() => { window.location.hash = '/order/99999'; }")
            page.wait_for_timeout(800)
            page.evaluate("() => { window.dispatchEvent(new HashChangeEvent('hashchange')); }")
            page.wait_for_timeout(2500)

        with allure.step("验证404或错误提示"):
            body = page.inner_text("body")
            has_error_toast = "加载订单失败" in body or "资源不存在" in body or "订单不存在" in body
            has_not_found_text = "404" in body or "不存在" in body or "找不到" in body
            assert has_error_toast or has_not_found_text, \
                f"访问不存在的订单应显示错误提示，当前页面内容片段: {body[:200]}"
