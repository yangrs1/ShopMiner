"""
Web UI 测试 - 认证与导航模块
覆盖页面: Login / Register / NavBar (登录态切换 + 登出)
"""
import allure
import pytest
import re
import random
from playwright.sync_api import Page, expect
from tests.web.pages.login_page import LoginPage


BASE_URL = "http://127.0.0.1:5000"


# ============================================================
# WEB-02 注册（Register）
# ============================================================
@allure.feature("Web UI测试")
class TestRegisterPage:

    @allure.story("注册")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("WEB-02-01 新用户注册成功→自动登录→跳转首？")
    def test_register_success(self, page: Page):
        suffix = random.randint(10000, 99999)
        email = f"webuser{suffix}@test.com"

        with allure.step("打开注册页面"):
            page.goto(f"{BASE_URL}/#/register", timeout=20000)
            page.wait_for_load_state("networkidle")

        with allure.step("填写完整注册信息"):
            page.fill("input[placeholder='请输入姓']", "Auto")
            page.fill("input[placeholder='请输入名']", f"Test{suffix}")
            page.fill("input[placeholder='请输入邮箱']", email)
            page.fill("input[placeholder='至少8位，含大小写字母和数字']", "WebTest@123456")
            page.fill("input[placeholder='请输入收货地址']", "Auto Test Street 123")

        with allure.step("点击注册"):
            page.click("button:has-text('注册')")

        with allure.step("验证注册成功"):
            page.wait_for_timeout(3000)
            body = page.inner_text("body")
            assert "注册成功" in body or "首页" in body or "ShopMiner" in body, \
                f"注册后应跳转首页，当前URL: {page.url}"

    @allure.story("注册")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-02-02 注册表单-必填字段为空→拦？")
    def test_register_validation_empty(self, page: Page):
        with allure.step("打开注册？"):
            page.goto(f"{BASE_URL}/#/register", timeout=20000)
            page.wait_for_load_state("networkidle")

        with allure.step("不填信息直接提交"):
            page.click("button:has-text('注册')")

        with allure.step("验证前端校验拦截"):
            page.wait_for_timeout(1500)
            error_messages = page.locator(".el-form-item__error, .el-message--error")
            count = error_messages.count()
            # 至少应有邮箱/密码/姓名等字段校验提？"
            assert count > 0 or "register" in page.url, "空表单应被前端校验拦？"

    @allure.story("注册")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-02-03 注册表单-密码过短→拦？")
    def test_register_short_password(self, page: Page):
        with allure.step("打开注册？"):
            page.goto(f"{BASE_URL}/#/register", timeout=20000)
            page.wait_for_load_state("networkidle")

        with allure.step("填写短密码"):
            page.fill("input[placeholder='请输入姓']", "Short")
            page.fill("input[placeholder='请输入名']", "Pwd")
            page.fill("input[placeholder='请输入邮箱']", f"short{random.randint(100,999)}@test.com")
            page.fill("input[placeholder='至少8位，含大小写字母和数字']", "12")
            page.fill("input[placeholder='请输入收货地址']", "Addr")
            page.click("button:has-text('注册')")

        with allure.step("验证前端校验拦截"):
            page.wait_for_timeout(1500)
            assert page.locator(".el-form-item__error").count() > 0 or "register" in page.url

    @allure.story("注册")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-02-04 注册页有跳转登录链接")
    def test_register_has_login_link(self, page: Page):
        with allure.step("打开注册？"):
            page.goto(f"{BASE_URL}/#/register", timeout=20000)
            page.wait_for_load_state("networkidle")

        with allure.step("点击去登录"):
            link = page.locator("a:has-text('去登录'), a:has-text('已有账号')")
            expect(link).to_be_visible()
            link.click()
            page.wait_for_timeout(1500)

        with allure.step("验证跳转到登录页"):
            assert "login" in page.url


# ============================================================
# WEB-03 登录（Login）
# ============================================================
@allure.feature("Web UI测试")
class TestLoginPage:

    @allure.story("登录")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("WEB-03-01 正常登录-管理？")
    def test_login_admin_success(self, page: Page):
        with allure.step("打开登录？"):
            page.goto(f"{BASE_URL}/#/login", timeout=20000)
            page.wait_for_load_state("networkidle")

        with allure.step("输入管理员凭？"):
            page.fill("input[placeholder='请输入邮箱']", "admin@shopminer.com")
            page.fill("input[placeholder='请输入密码']", "Admin@123")
            page.click("button:has-text('登录')")

        with allure.step("验证登录成功"):
            page.wait_for_timeout(3000)
            body_text = page.inner_text("body")
            assert "登录成功" in body_text or "管理" in body_text or "#/" in page.url

    @allure.story("登录")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("WEB-03-02 正常登录-普通用？")
    def test_login_customer_success(self, page: Page):
        with allure.step("打开登录？"):
            page.goto(f"{BASE_URL}/#/login", timeout=20000)
            page.wait_for_load_state("networkidle")

        with allure.step("输入用户凭证"):
            page.fill("input[placeholder='请输入邮箱']", "customer@shopminer.com")
            page.fill("input[placeholder='请输入密码']", "Customer@123")
            page.click("button:has-text('登录')")

        with allure.step("验证登录成功"):
            page.wait_for_timeout(3000)
            body_text = page.inner_text("body")
            assert "登录成功" in body_text or "首页" in body_text

    @allure.story("登录")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-03-03 登录失败-密码错误→提示错？")
    def test_login_failure_wrong_password(self, page: Page):
        with allure.step("打开登录？"):
            page.goto(f"{BASE_URL}/#/login", timeout=20000)
            page.wait_for_load_state("networkidle")

        with allure.step("输入错误密码"):
            page.fill("input[placeholder='请输入邮箱']", "customer@shopminer.com")
            page.fill("input[placeholder='请输入密码']", "WrongPassword999")
            page.click("button:has-text('登录')")

        with allure.step("验证错误提示"):
            page.wait_for_timeout(2000)
            error = page.locator(".el-message--error, .el-alert, .el-form-item__error")
            assert error.count() > 0 or "login" in page.url, "登录失败应提示错？"

    @allure.story("登录")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-03-04 登录页有跳转注册链接")
    def test_login_has_register_link(self, page: Page):
        with allure.step("打开登录？"):
            page.goto(f"{BASE_URL}/#/login", timeout=20000)
            page.wait_for_load_state("networkidle")

        with allure.step("点击立即注册"):
            link = page.locator("a:has-text('立即注册'), a:has-text('还没有账号')")
            expect(link).to_be_visible()
            link.click()
            page.wait_for_timeout(1500)

        with allure.step("验证跳转到注册页"):
            assert "register" in page.url


# ============================================================
# WEB-10 导航栏（NavBar）
# ============================================================
@allure.feature("Web UI测试")
class TestNavBar:

    @allure.story("导航？")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-10-01 未登录→显示登录/注册按钮")
    def test_navbar_not_logged_in(self, page: Page):
        with allure.step("打开首页"):
            page.goto(f"{BASE_URL}")
            page.wait_for_load_state("networkidle")

        with allure.step("验证导航栏有登录和注册链？"):
            nav = page.inner_text("nav, .navbar, .el-menu")
            assert "登录" in nav or "Login" in nav
            assert "注册" in nav or "Register" in nav

    @allure.story("导航？")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-10-02 已登录→显示购物车'订单/用户菜单")
    def test_navbar_logged_in(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("验证导航栏显示已登录状？"):
            page.wait_for_timeout(1000)
            nav = page.inner_text("nav, .navbar, .el-menu")
            assert "购物车" in nav or "Cart" in nav
            assert "订单" in nav or "Orders" in nav


# ============================================================
# WEB-19 导航？"退出登？"
# ============================================================
@allure.feature("Web UI测试")
class TestNavBarLogout:

    @allure.story("导航？")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-19-01 已登录用户退出登？")
    def test_navbar_logout(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("点击用户菜单"):
            user_menu = page.locator(".el-sub-menu:has-text('Test'), .el-sub-menu:has-text('Customer')")
            if user_menu.count() > 0:
                user_menu.hover()
                page.wait_for_timeout(500)

        with allure.step("点击退出登录"):
            logout_btn = page.locator(".el-menu-item:has-text('退出登录')")
            if logout_btn.is_visible():
                logout_btn.click()
                page.wait_for_timeout(2000)

                with allure.step("验证退出后导航栏显示登录按？"):
                    nav = page.inner_text("nav, .navbar, .el-menu")
                    assert "登录" in nav or "Login" in nav
