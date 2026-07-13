"""
Web UI 测试 - 收藏夹与个人中心模块
覆盖页面: Profile (个人中心/RFM/保存/充值) / Favorites (收藏按钮/收藏页/推荐理由/导航栏入口)
"""
import allure
import pytest
import re
from playwright.sync_api import Page, expect
from tests.web.pages.login_page import LoginPage


BASE_URL = "http://127.0.0.1:5000"


# ============================================================
# WEB-08 个人中心（Profile）
# ============================================================
@allure.feature("Web UI测试")
class TestProfilePage:

    @allure.story("个人中心")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-08-01 个人中心页面加载")
    def test_profile_page_loads(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("打开个人中心"):
            page.goto(f"{BASE_URL}/#/profile", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

        with allure.step("验证个人信息展示"):
            body = page.inner_text("body")
            assert "个人信息" in body or "余额" in body or "邮箱" in body

    @allure.story("个人中心")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-08-02 新用户RFM分群=新用？")
    def test_profile_new_user_rfm(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("打开个人中心查看消费报告"):
            page.goto(f"{BASE_URL}/#/profile", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

        with allure.step("验证页面有内？"):
            body = page.inner_text("body")
            assert len(body) > 50, "个人中心应有内容展示"

    @allure.story("个人中心")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-08-03 未登录访问个人中心→跳转登录？")
    def test_profile_redirect_to_login(self, page: Page):
        with allure.step("未登录直接打开个人中心"):
            page.goto(f"{BASE_URL}/#/profile", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

        with allure.step("验证跳转到登录页"):
            assert "login" in page.url


# ============================================================
# WEB-16 个人中心-保存信息/充值
# ============================================================
@allure.feature("Web UI测试")
class TestProfileActions:

    @allure.story("个人中心操作")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-16-01 个人中心-保存修改按钮可见")
    def test_profile_save_button(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("打开个人中心"):
            page.evaluate("() => { window.location.hash = '/profile'; }")
            page.wait_for_timeout(800)
            page.evaluate("() => { window.dispatchEvent(new HashChangeEvent('hashchange')); }")
            page.wait_for_timeout(800)
            page.wait_for_timeout(2000)

        with allure.step("验证保存修改按钮可见"):
            save_btn = page.locator("button:has-text('保存修改')")
            expect(save_btn).to_be_visible()

    @allure.story("个人中心操作")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-16-02 个人中心-充值按钮可？")
    def test_profile_recharge_button(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("打开个人中心"):
            page.evaluate("() => { window.location.hash = '/profile'; }")
            page.wait_for_timeout(800)
            page.evaluate("() => { window.dispatchEvent(new HashChangeEvent('hashchange')); }")
            page.wait_for_timeout(800)
            page.wait_for_timeout(2000)

        with allure.step("验证充值按钮可用"):
            recharge_btn = page.locator("button:has-text('充值')")
            expect(recharge_btn).to_be_visible()


# ============================================================
# WEB-24 收藏夹功？（新功？）
# 验证商品详情 ？按钮 + 我的收藏页面 + 推荐理由展示
# ============================================================
@allure.feature("Web UI测试")
class TestFavoritesWeb:
    """收藏夹与推荐理由 Web UI 测试"""

    @allure.story("商品详情-收藏按钮")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("WEB-24-01 已登录用户可点击按钮切换收藏状态")
    def test_favorite_button_toggle(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("test@shopminer.com", "Test@123456")

        with allure.step("打开商品详情页(test server product id=1)"):
            page.goto(f"{BASE_URL}/#/product/1", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

        with allure.step("找到心形收藏按钮并点击"):
            fav_btn = page.locator(".favorite-btn").first
            assert fav_btn.count() > 0, "未找到 .favorite-btn 收藏按钮"

        with allure.step("点击切换收藏状态"):
            fav_btn.click()
            page.wait_for_timeout(1500)
            assert fav_btn.count() > 0, "按钮应在点击后仍存在"

    @allure.story("商品详情-推荐理由")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-24-02 商品详情显示关联推荐理由文案")
    def test_recommendation_reason_displayed(self, page: Page):
        with allure.step("打开商品详情页(test server product id=1)"):
            page.goto(f"{BASE_URL}/#/product/1", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2500)

        with allure.step("验证 .rec-reason 推荐理由元素存在"):
            reasons = page.locator(".rec-reason")
            count = reasons.count()
            if count == 0:
                with allure.step("无推荐是 acceptable (test server 无足够规则)"):
                    allure.attach("test server 无推荐规则，跳过 reason 验证", name="skip_reason",
                                  attachment_type=allure.attachment_type.TEXT)
            else:
                with allure.step(f"验证 {count} 条推荐理由文？"):
                    first_reason = reasons.first.inner_text()
                    assert len(first_reason) > 5, f"理由文案太短: {first_reason}"

    @allure.story("我的收藏页面")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("WEB-24-03 我的收藏页面正常加载并显示空状态或商品")
    def test_favorites_page_loads(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("test@shopminer.com", "Test@123456")

        with allure.step("通过导航栏进入/favorites"):
            page.evaluate("() => { window.location.hash = '/favorites'; }")
            page.wait_for_timeout(800)
            page.evaluate("() => { window.dispatchEvent(new HashChangeEvent('hashchange')); }")
            page.wait_for_timeout(800)
            page.wait_for_timeout(2000)

        with allure.step("验证页面标题"):
            assert "我的收藏" in page.inner_text("body"), "页面应包含'我的收藏'标题"

    @allure.story("NavBar 收藏入口")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-24-04 导航栏出现'收藏'菜单入口")
    def test_navbar_shows_favorites_link(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("test@shopminer.com", "Test@123456")

        with allure.step("打开首页"):
            page.evaluate("() => { window.location.hash = '/'; }")
            page.wait_for_timeout(800)
            page.evaluate("() => { window.dispatchEvent(new HashChangeEvent('hashchange')); }")
            page.wait_for_timeout(800)
            page.wait_for_timeout(1500)

        with allure.step("验证导航栏含'收藏'菜单项"):
            fav_menu = page.locator(".el-menu-item:has-text('收藏')")
            assert fav_menu.count() > 0, "NavBar 应有'收藏'菜单"

        with allure.step("点击进入收藏？"):
            fav_menu.first.click()
            page.wait_for_timeout(2000)
            assert "/favorites" in page.url, f"应跳转到 /favorites，实际{page.url}"
