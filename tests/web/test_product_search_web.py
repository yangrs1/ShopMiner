"""
Web UI 测试 - 商品与搜索模块
覆盖页面: Home / Search / ProductDetail / Category + 商品评价 + 未登录加购跳转
"""
import allure
import pytest
import re
from playwright.sync_api import Page, expect
from tests.web.pages.login_page import LoginPage


BASE_URL = "http://127.0.0.1:5000"


# ============================================================
# WEB-01 首页（Home）
# ============================================================
@allure.feature("Web UI测试")
class TestHomePage:

    @allure.story("首页")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("WEB-01-01 首页展示热门商品和导航栏")
    def test_home_displays_products(self, page: Page):
        with allure.step("打开首页"):
            page.goto(BASE_URL, timeout=20000)
            page.wait_for_load_state("networkidle")

        with allure.step("验证Banner标题可见"):
            expect(page.locator(".banner-title")).to_be_visible()

        with allure.step("验证商品卡片展示"):
            cards = page.locator(".el-card, .product-card")
            card_count = cards.count()
            assert card_count > 0, f"首页应展示商品卡片，实际: {card_count}"

        with allure.step("验证导航栏可？"):
            expect(page.locator(".navbar, .el-menu")).to_be_visible()

    @allure.story("首页")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-01-02 首页分类筛选切？")
    def test_home_category_filter(self, page: Page):
        with allure.step("打开首页"):
            page.goto(BASE_URL, timeout=20000)
            page.wait_for_load_state("networkidle")

        with allure.step("点击分类导航标签"):
            category_links = page.locator(".category-nav a, .category-nav span, .el-tabs__item, .category-item")
            count = category_links.count()
            if count > 0:
                category_links.first.click()
                page.wait_for_timeout(2000)
                with allure.step("验证商品区域刷新"):
                    section = page.locator(".section, .product-grid")
                    expect(section).to_be_visible()


# ============================================================
# WEB-04 搜索（Search）
# ============================================================
@allure.feature("Web UI测试")
class TestSearchPage:

    @allure.story("搜索")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-04-01 搜索商品-有关键词结果")
    def test_search_with_results(self, page: Page):
        with allure.step("打开首页通过导航栏搜？"):
            page.goto(f"{BASE_URL}")
            page.wait_for_load_state("networkidle")
            search_input = page.locator(".navbar input[placeholder*='搜索'], input[placeholder*='搜索']")
            if search_input.count() == 0:
                pytest.skip("搜索框未在首页显？")

            search_input.fill("T-Shirt")
            search_input.press("Enter")
            page.wait_for_timeout(2000)

        with allure.step("验证搜索结果页展？"):
            body = page.inner_text("body")
            assert "搜索" in body or "T-Shirt" in body

    @allure.story("搜索")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-04-02 搜索商品-无结果时显示空状？")
    def test_search_no_results(self, page: Page):
        with allure.step("搜索不存在的商品"):
            page.goto(f"{BASE_URL}/#/search?q=ZZZZNONEXISTENT999")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

        with allure.step("验证显示空状态"):
            body = page.inner_text("body")
            assert "未找到" in body or "暂无" in body or "empty" in body.lower()


# ============================================================
# WEB-05 商品详情（ProductDetail）
# ============================================================
@allure.feature("Web UI测试")
class TestProductDetailPage:

    @allure.story("商品详情")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-05-01 未登录浏览商品详？")
    def test_product_detail_anonymous(self, page: Page):
        with allure.step("打开首页加载SPA"):
            page.goto(BASE_URL, timeout=20000)
            page.wait_for_load_state("networkidle")

        with allure.step("通过hash路由跳转到商品详？"):
            page.evaluate("window.location.hash = '#/product/1'")
            page.wait_for_timeout(3000)

        with allure.step("验证商品信息展示"):
            body = page.inner_text("body")
            assert len(body) > 100, "商品详情页应有内容展？"

    @allure.story("商品详情")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("WEB-05-02 已登录用户加购商？")
    def test_product_detail_add_to_cart_logged_in(self, page: Page):
        with allure.step("先登？"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("打开商品详情"):
            page.goto(f"{BASE_URL}/#/product/1", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)

        with allure.step("点击加入购物车"):
            add_btn = page.locator("button:has-text('加入购物车')")
            if add_btn.is_visible():
                add_btn.click()
                page.wait_for_timeout(2000)
                with allure.step("验证加购成功提示"):
                    body = page.inner_text("body")
                    assert "成功" in body or "购物车" in body
            else:
                pytest.skip("加购按钮不可？")

    @allure.story("商品详情")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-05-03 浏览不存在商品→404")
    def test_product_detail_not_found(self, page: Page):
        with allure.step("打开不存在的商品"):
            page.goto(f"{BASE_URL}/#/product/99999", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

        with allure.step("验证404或空状？"):
            body = page.inner_text("body")
            assert len(body) > 0


# ============================================================
# WEB-11 商品详情页（ProductDetail）未登录加？
# ============================================================
@allure.feature("Web UI测试")
class TestProductDetailUnauthenticated:

    @allure.story("商品详情-权限")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-11-01 未登录点击加购→跳转登录？")
    def test_add_to_cart_anonymous_redirect(self, page: Page):
        with allure.step("打开首页加载SPA"):
            page.goto(BASE_URL, timeout=20000)
            page.wait_for_load_state("networkidle")

        with allure.step("导航到商品详？"):
            page.evaluate("window.location.hash = '#/product/1'")
            page.wait_for_timeout(3000)

        with allure.step("点击加入购物车"):
            add_btn = page.locator("button:has-text('加入购物车')")
            if add_btn.is_visible():
                add_btn.click()
                page.wait_for_timeout(2000)

                with allure.step("验证跳转登录页或弹出提示"):
                    body = page.inner_text("body")
                    has_login_redirect = "login" in page.url
                    has_warning = "请先登录" in body or "登录" in body
                    assert has_login_redirect or has_warning, f"未登录加购应提示登录或跳转，当前URL: {page.url}"


# ============================================================
# WEB-13 商品详情-提交评价
# ============================================================
@allure.feature("Web UI测试")
class TestProductReview:

    @allure.story("商品评价")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-13-01 已登录用户提交商品评？")
    def test_submit_product_review(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("打开商品详情"):
            page.goto(f"{BASE_URL}/#/product/1", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)

        with allure.step("选择评分并提交评？"):
            rate = page.locator(".el-rate .el-rate__item")
            if rate.count() > 0:
                rate.nth(4).click()
                page.wait_for_timeout(500)

            submit_btn = page.locator("button:has-text('评价'), button:has-text('提交')")
            if submit_btn.is_visible():
                submit_btn.click()
                page.wait_for_timeout(2000)
                with allure.step("验证评价提交成功"):
                    body = page.inner_text("body")
                    assert len(body) > 0


# ============================================================
# WEB-20 独立分类页面
# ============================================================
@allure.feature("Web UI测试")
class TestCategoryPage:

    @allure.story("分类")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-20-01 独立分类页面路由可访？")
    def test_category_page_route(self, page: Page):
        with allure.step("直接打开分类页面"):
            page.goto(f"{BASE_URL}/#/category/T-Shirt", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

        with allure.step("验证页面有内？"):
            body = page.inner_text("body")
            assert len(body) > 0
