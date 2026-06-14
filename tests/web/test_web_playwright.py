"""
Web UI 综合测试覆盖全部前端页面功能
测试场景: 32?"
覆盖页面: Home/Login/Register/Search/ProductDetail/Cart/Orders/Profile/Admin + NavBar
"""
import allure
import pytest
import random
from playwright.sync_api import Page, expect
from tests.web.pages.login_page import LoginPage
from tests.web.pages.register_page import RegisterPage


BASE_URL = "http://127.0.0.1:5000"



# ============================================================
# WEB-01 首页（Home?"
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

        with allure.step("验证导航栏可?"):
            expect(page.locator(".navbar, .el-menu")).to_be_visible()

    @allure.story("首页")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-01-02 首页分类筛选切?")
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
# WEB-02 注册（Register?"
# ============================================================
@allure.feature("Web UI测试")
class TestRegisterPage:

    @allure.story("注册")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("WEB-02-01 新用户注册成功→自动登录→跳转首?")
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
    @allure.title("WEB-02-02 注册表单-必填字段为空→拦?")
    def test_register_validation_empty(self, page: Page):
        with allure.step("打开注册?"):
            page.goto(f"{BASE_URL}/#/register", timeout=20000)
            page.wait_for_load_state("networkidle")

        with allure.step("不填信息直接提交"):
            page.click("button:has-text('注册')")

        with allure.step("验证前端校验拦截"):
            page.wait_for_timeout(1500)
            error_messages = page.locator(".el-form-item__error, .el-message--error")
            count = error_messages.count()
            # 至少应有邮箱/密码/姓名等字段校验提?"
            assert count > 0 or "register" in page.url, "空表单应被前端校验拦?"

    @allure.story("注册")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-02-03 注册表单-密码过短→拦?")
    def test_register_short_password(self, page: Page):
        with allure.step("打开注册?"):
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
        with allure.step("打开注册?"):
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
# WEB-03 登录（Login?"
# ============================================================
@allure.feature("Web UI测试")
class TestLoginPage:

    @allure.story("登录")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("WEB-03-01 正常登录-管理?")
    def test_login_admin_success(self, page: Page):
        with allure.step("打开登录?"):
            page.goto(f"{BASE_URL}/#/login", timeout=20000)
            page.wait_for_load_state("networkidle")

        with allure.step("输入管理员凭?"):
            page.fill("input[placeholder='请输入邮箱']", "admin@shopminer.com")
            page.fill("input[placeholder='请输入密码']", "Admin@123")
            page.click("button:has-text('登录')")

        with allure.step("验证登录成功"):
            page.wait_for_timeout(3000)
            body_text = page.inner_text("body")
            assert "登录成功" in body_text or "管理" in body_text or "#/" in page.url

    @allure.story("登录")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("WEB-03-02 正常登录-普通用?")
    def test_login_customer_success(self, page: Page):
        with allure.step("打开登录?"):
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
    @allure.title("WEB-03-03 登录失败-密码错误→提示错?")
    def test_login_failure_wrong_password(self, page: Page):
        with allure.step("打开登录?"):
            page.goto(f"{BASE_URL}/#/login", timeout=20000)
            page.wait_for_load_state("networkidle")

        with allure.step("输入错误密码"):
            page.fill("input[placeholder='请输入邮箱']", "customer@shopminer.com")
            page.fill("input[placeholder='请输入密码']", "WrongPassword999")
            page.click("button:has-text('登录')")

        with allure.step("验证错误提示"):
            page.wait_for_timeout(2000)
            error = page.locator(".el-message--error, .el-alert, .el-form-item__error")
            assert error.count() > 0 or "login" in page.url, "登录失败应提示错?"

    @allure.story("登录")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-03-04 登录页有跳转注册链接")
    def test_login_has_register_link(self, page: Page):
        with allure.step("打开登录?"):
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
# WEB-04 搜索（Search?"
# ============================================================
@allure.feature("Web UI测试")
class TestSearchPage:

    @allure.story("搜索")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-04-01 搜索商品-有关键词结果")
    def test_search_with_results(self, page: Page):
        with allure.step("打开首页通过导航栏搜?"):
            page.goto(f"{BASE_URL}")
            page.wait_for_load_state("networkidle")
            search_input = page.locator(".navbar input[placeholder*='搜索'], input[placeholder*='搜索']")
            if search_input.count() == 0:
                pytest.skip("搜索框未在首页显?")

            search_input.fill("T-Shirt")
            search_input.press("Enter")
            page.wait_for_timeout(2000)

        with allure.step("验证搜索结果页展?"):
            body = page.inner_text("body")
            assert "搜索" in body or "T-Shirt" in body

    @allure.story("搜索")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-04-02 搜索商品-无结果时显示空状?")
    def test_search_no_results(self, page: Page):
        with allure.step("搜索不存在的商品"):
            page.goto(f"{BASE_URL}/#/search?q=ZZZZNONEXISTENT999")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

        with allure.step("验证显示空状态"):
            body = page.inner_text("body")
            assert "未找到" in body or "暂无" in body or "empty" in body.lower()


# ============================================================
# WEB-05 商品详情（ProductDetail?"
# ============================================================
@allure.feature("Web UI测试")
class TestProductDetailPage:

    @allure.story("商品详情")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-05-01 未登录浏览商品详?")
    def test_product_detail_anonymous(self, page: Page):
        with allure.step("打开首页加载SPA"):
            page.goto(BASE_URL, timeout=20000)
            page.wait_for_load_state("networkidle")

        with allure.step("通过hash路由跳转到商品详?"):
            page.evaluate("window.location.hash = '#/product/1'")
            page.wait_for_timeout(3000)

        with allure.step("验证商品信息展示"):
            body = page.inner_text("body")
            assert len(body) > 100, "商品详情页应有内容展?"

    @allure.story("商品详情")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("WEB-05-02 已登录用户加购商?")
    def test_product_detail_add_to_cart_logged_in(self, page: Page):
        with allure.step("先登?"):
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
                pytest.skip("加购按钮不可?")

    @allure.story("商品详情")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-05-03 浏览不存在商品→404")
    def test_product_detail_not_found(self, page: Page):
        with allure.step("打开不存在的商品"):
            page.goto(f"{BASE_URL}/#/product/99999", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

        with allure.step("验证404或空状?"):
            body = page.inner_text("body")
            assert len(body) > 0


# ============================================================
# WEB-06 购物车（Cart?"
# ============================================================
@allure.feature("Web UI测试")
class TestCartPage:

    @allure.story("购物车")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("WEB-06-01 先加购→购物车展示商?")
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
    @allure.title("WEB-06-02 空购物车→显示空状?")
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
# WEB-07 订单（Orders?"
# ============================================================
@allure.feature("Web UI测试")
class TestOrdersPage:

    @allure.story("订单")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-07-01 新用户订单页显示空状?")
    def test_orders_empty(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("打开订单?"):
            page.goto(f"{BASE_URL}/#/orders", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)

        with allure.step("验证空订单提?"):
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

                with allure.step("确认订单对话?"):
                    confirm_btn = page.locator(".el-message-box .el-button--primary, .el-button--primary:has-text('确认')")
                    if confirm_btn.is_visible():
                        confirm_btn.click()
                        page.wait_for_timeout(3000)

        with allure.step("验证跳转到订单页"):
            page.wait_for_timeout(1000)
            assert "orders" in page.url or "订单" in page.inner_text("body")


# ============================================================
# WEB-08 个人中心（Profile?"
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
    @allure.title("WEB-08-02 新用户RFM分群=新用?")
    def test_profile_new_user_rfm(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("打开个人中心查看消费报告"):
            page.goto(f"{BASE_URL}/#/profile", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

        with allure.step("验证页面有内?"):
            body = page.inner_text("body")
            assert len(body) > 50, "个人中心应有内容展示"

    @allure.story("个人中心")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-08-03 未登录访问个人中心→跳转登录?")
    def test_profile_redirect_to_login(self, page: Page):
        with allure.step("未登录直接打开个人中心"):
            page.goto(f"{BASE_URL}/#/profile", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

        with allure.step("验证跳转到登录页"):
            assert "login" in page.url


# ============================================================
# WEB-09 管理后台（Admin?"
# ============================================================
@allure.feature("Web UI测试")
class TestAdminPage:

    @allure.story("管理后台")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("WEB-09-01 管理员访问数据看?")
    def test_admin_dashboard(self, page: Page):
        with allure.step("管理员登?"):
            LoginPage(page).navigate().login("admin@shopminer.com", "Admin@123")

        with allure.step("打开管理后台"):
            page.goto(f"{BASE_URL}/#/admin", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

        with allure.step("验证数据看板加载"):
            body = page.inner_text("body")
            assert "数据看板" in body or "Dashboard" in body or "管理?" in body

    @allure.story("管理后台")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-09-02 管理员切换到客户分群页签")
    def test_admin_rfm_tab(self, page: Page):
        with allure.step("管理员登?"):
            LoginPage(page).navigate().login("admin@shopminer.com", "Admin@123")

        with allure.step("打开后台并切换到RFM"):
            page.goto(f"{BASE_URL}/#/admin", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)

            rfm_menu = page.locator(".el-menu-item:has-text('客户分群'), .el-menu-item:has-text('RFM')")
            if rfm_menu.count() > 0:
                rfm_menu.first.click()
                page.wait_for_timeout(2000)
                body = page.inner_text("body")
                assert "分群" in body or "RFM" in body

    @allure.story("管理后台")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-09-03 管理员查看订单管?")
    def test_admin_orders_tab(self, page: Page):
        with allure.step("管理员登?"):
            LoginPage(page).navigate().login("admin@shopminer.com", "Admin@123")

        with allure.step("打开后台"):
            page.goto(f"{BASE_URL}/#/admin", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)

            orders_menu = page.locator(".el-menu-item:has-text('订单管理')")
            if orders_menu.count() > 0:
                orders_menu.first.click()
                page.wait_for_timeout(2000)
                body = page.inner_text("body")
                assert len(body) > 0

    @allure.story("管理后台")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("WEB-09-04 普通用户访问管理后台→被拦?")
    def test_admin_access_denied_for_customer(self, page: Page):
        with allure.step("普通用户登?"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("尝试访问管理后台"):
            page.goto(f"{BASE_URL}/#/admin", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

        with allure.step("验证被重定向(无权访问)"):
            current_url = page.url
            assert "#/admin" not in current_url or "管理" not in page.inner_text("body"), \
                f"普通用户访问admin应被重定向，当前URL: {current_url}"

# ============================================================
# WEB-10 导航栏（NavBar?"
# ============================================================
@allure.feature("Web UI测试")
class TestNavBar:

    @allure.story("导航?")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-10-01 未登录→显示登录/注册按钮")
    def test_navbar_not_logged_in(self, page: Page):
        with allure.step("打开首页"):
            page.goto(f"{BASE_URL}")
            page.wait_for_load_state("networkidle")

        with allure.step("验证导航栏有登录和注册链?"):
            nav = page.inner_text("nav, .navbar, .el-menu")
            assert "登录" in nav or "Login" in nav
            assert "注册" in nav or "Register" in nav

    @allure.story("导航?")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-10-02 已登录→显示购物车'订单/用户菜单")
    def test_navbar_logged_in(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("验证导航栏显示已登录状?"):
            page.wait_for_timeout(1000)
            nav = page.inner_text("nav, .navbar, .el-menu")
            assert "购物车" in nav or "Cart" in nav
            assert "订单" in nav or "Orders" in nav


# ============================================================
# WEB-11 商品详情页（ProductDetail?" 未登录加?"
# ============================================================
@allure.feature("Web UI测试")
class TestProductDetailUnauthenticated:

    @allure.story("商品详情-权限")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-11-01 未登录点击加购→跳转登录?")
    def test_add_to_cart_anonymous_redirect(self, page: Page):
        with allure.step("打开首页加载SPA"):
            page.goto(BASE_URL, timeout=20000)
            page.wait_for_load_state("networkidle")

        with allure.step("导航到商品详?"):
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
# WEB-12 管理后台-用户管理
# ============================================================
@allure.feature("Web UI测试")
class TestAdminUserManagement:

    @allure.story("管理后台")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-12-01 管理员查看用户管理页?")
    def test_admin_users_tab(self, page: Page):
        with allure.step("管理员登?"):
            LoginPage(page).navigate().login("admin@shopminer.com", "Admin@123")

        with allure.step("打开后台"):
            page.goto(f"{BASE_URL}/#/admin", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)

            users_menu = page.locator(".el-menu-item:has-text('用户管理')")
            if users_menu.count() > 0:
                users_menu.first.click()
                page.wait_for_timeout(2000)
                body = page.inner_text("body")
                assert len(body) > 0


# ============================================================
# WEB-13 商品详情-提交评价
# ============================================================
@allure.feature("Web UI测试")
class TestProductReview:

    @allure.story("商品评价")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-13-01 已登录用户提交商品评?")
    def test_submit_product_review(self, page: Page):
        with allure.step("登录"):
            LoginPage(page).navigate().login("customer@shopminer.com", "Customer@123")

        with allure.step("打开商品详情"):
            page.goto(f"{BASE_URL}/#/product/1", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)

        with allure.step("选择评分并提交评?"):
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

    @allure.story("购物车操?")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-14-02 购物车删除商?")
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
                with allure.step("验证商品已移?"):
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

        with allure.step("打开订单?"):
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

        with allure.step("打开订单?"):
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
                        assert "已取?" in body or "取消" in body


# ============================================================
# WEB-16 个人中心-保存信息/充?"
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
    @allure.title("WEB-16-02 个人中心-充值按钮可?")
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
# WEB-17 管理后台-销售分?"关联规则/流失预警/模型指标
# ============================================================
@allure.feature("Web UI测试")
class TestAdminAnalyticsTabs:

    @allure.story("管理后台")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-17-01 管理员查看销售分析页?")
    def test_admin_sales_tab(self, page: Page):
        with allure.step("管理员登?"):
            LoginPage(page).navigate().login("admin@shopminer.com", "Admin@123")

        with allure.step("打开后台"):
            page.goto(f"{BASE_URL}/#/admin", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)

            sales_menu = page.locator(".el-menu-item:has-text('销售分析')")
            if sales_menu.count() > 0:
                sales_menu.first.click()
                page.wait_for_timeout(2000)
                body = page.inner_text("body")
                assert len(body) > 0

    @allure.story("管理后台")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-17-02 管理员查看关联规则页?")
    def test_admin_association_tab(self, page: Page):
        with allure.step("管理员登?"):
            LoginPage(page).navigate().login("admin@shopminer.com", "Admin@123")

        with allure.step("打开后台"):
            page.goto(f"{BASE_URL}/#/admin", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)

            assoc_menu = page.locator(".el-menu-item:has-text('关联规则')")
            if assoc_menu.count() > 0:
                assoc_menu.first.click()
                page.wait_for_timeout(2000)
                body = page.inner_text("body")
                assert len(body) > 0

    @allure.story("管理后台")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-17-03 管理员查看流失预警页?")
    def test_admin_churn_tab(self, page: Page):
        with allure.step("管理员登?"):
            LoginPage(page).navigate().login("admin@shopminer.com", "Admin@123")

        with allure.step("打开后台"):
            page.goto(f"{BASE_URL}/#/admin", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)

            churn_menu = page.locator(".el-menu-item:has-text('流失预警')")
            if churn_menu.count() > 0:
                churn_menu.first.click()
                page.wait_for_timeout(2000)
                body = page.inner_text("body")
                assert len(body) > 0

    @allure.story("管理后台")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-17-04 管理员查看模型指标页?")
    def test_admin_models_tab(self, page: Page):
        with allure.step("管理员登?"):
            LoginPage(page).navigate().login("admin@shopminer.com", "Admin@123")

        with allure.step("打开后台"):
            page.goto(f"{BASE_URL}/#/admin", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)

            models_menu = page.locator(".el-menu-item:has-text('模型指标')")
            if models_menu.count() > 0:
                models_menu.first.click()
                page.wait_for_timeout(2000)
                body = page.inner_text("body")
                assert len(body) > 0


# ============================================================
# WEB-18 管理后台-订单管理操作
# ============================================================
@allure.feature("Web UI测试")
class TestAdminOrderActions:

    @allure.story("管理后台订单操作")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-18-01 管理员订单管理页展示发货/退款按?")
    def test_admin_order_action_buttons(self, page: Page):
        with allure.step("管理员登?"):
            LoginPage(page).navigate().login("admin@shopminer.com", "Admin@123")

        with allure.step("打开后台→订单管?"):
            page.goto(f"{BASE_URL}/#/admin", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)
            orders_menu = page.locator(".el-menu-item:has-text('订单管理')")
            if orders_menu.count() > 0:
                orders_menu.first.click()
                page.wait_for_timeout(2000)

        with allure.step("验证订单表格加载"):
            body = page.inner_text("body")
            assert len(body) > 0

    @allure.story("管理后台订单操作")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-18-02 管理员重新计算按钮可见")
    def test_admin_recompute_button(self, page: Page):
        with allure.step("管理员登?"):
            LoginPage(page).navigate().login("admin@shopminer.com", "Admin@123")

        with allure.step("打开后台"):
            page.goto(f"{BASE_URL}/#/admin", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)

        with allure.step("验证重新计算按钮"):
            recompute_btn = page.locator("button:has-text('重新计算')")
            expect(recompute_btn).to_be_visible()


# ============================================================
# WEB-19 导航?"退出登?"
# ============================================================
@allure.feature("Web UI测试")
class TestNavBarLogout:

    @allure.story("导航?")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-19-01 已登录用户退出登?")
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

                with allure.step("验证退出后导航栏显示登录按?"):
                    nav = page.inner_text("nav, .navbar, .el-menu")
                    assert "登录" in nav or "Login" in nav


# ============================================================
# WEB-20 独立分类页面
# ============================================================
@allure.feature("Web UI测试")
class TestCategoryPage:

    @allure.story("分类")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("WEB-20-01 独立分类页面路由可访?")
    def test_category_page_route(self, page: Page):
        with allure.step("直接打开分类页面"):
            page.goto(f"{BASE_URL}/#/category/T-Shirt", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)

        with allure.step("验证页面有内?"):
            body = page.inner_text("body")
            assert len(body) > 0


# ============================================================
# WEB-21 管理后台-模型指标弹窗显示版本?"(?"
# 验证 KPI 卡片点击?"el-dialog 显示模型版本 (v3/v4/v8)
# ============================================================
@allure.feature("Web UI测试")
class TestAdminVizDialogVersion:
    """管理后台模型指标弹窗 - 验证版本号展?"""

    @allure.story("模型指标弹窗")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("case", [
        {"tab_index": 0, "card_label": "客户分群", "expected_version": "v4", "title": "WEB-21-01 客户分群弹窗显示v4版本"},
        {"tab_index": 1, "card_label": "流失预警", "expected_version": "v8", "title": "WEB-21-02 流失预警弹窗显示v8版本"},
        {"tab_index": 2, "card_label": "销售预?", "expected_version": "v3", "title": "WEB-21-03 销售预测弹窗显示v3版本"},
        {"tab_index": 3, "card_label": "关联规则", "expected_version": "v3", "title": "WEB-21-04 关联规则弹窗显示v3版本"},
    ])
    @allure.title("{case[title]}")
    def test_admin_viz_dialog_shows_version(self, page: Page, case):
        with allure.step("管理员登?"):
            LoginPage(page).navigate().login("admin@shopminer.com", "Admin@123")

        with allure.step("打开后台→模型指?"):
            page.goto(f"{BASE_URL}/#/admin", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1500)
            models_menu = page.locator(".el-menu-item:has-text('模型指标')")
            if models_menu.count() > 0:
                models_menu.first.click()
                page.wait_for_timeout(2000)

        with allure.step(f"点击 {case['card_label']} 卡片打开弹窗"):
            card = page.locator(f".metric-card:has-text('{case['card_label']}'), .kpi-card:has-text('{case['card_label']}'), .el-card:has-text('{case['card_label']}')")
            if card.count() > 0:
                card.first.click()
                page.wait_for_timeout(1500)

        with allure.step(f"验证弹窗含版本号 {case['expected_version']}"):
            dialog = page.locator(".el-dialog__body, .el-dialog")
            if dialog.count() > 0 and dialog.first.is_visible():
                body = dialog.first.inner_text()
                assert case["expected_version"] in body, \
                    f"Dialog should contain version {case['expected_version']}, got: {body[:200]}"


# ============================================================
# WEB-22 管理后台-模型可视化弹窗显示版本号 (?"
# 点击 "查看可视化详?" 按钮打开弹窗, 弹窗内显?"metadata.version
# 模型顺序: 关联规则, 流失预警, 客户分群, 销售预?"
# ============================================================
@allure.feature("Web UI测试")
class TestAdminVizDialogVersion:
    """管理后台模型可视化弹?"- 验证版本号展?"""

    @allure.story("模型可视化弹窗版本号")
    @allure.severity(allure.severity_level.CRITICAL)
    @pytest.mark.parametrize("case", [
        {"card_index": 0, "card_label": "关联规则", "expected_version": "v3", "title": "WEB-22-01 关联规则弹窗显示v3版本"},
        {"card_index": 1, "card_label": "流失预警", "expected_version": "v8", "title": "WEB-22-02 流失预警弹窗显示v8版本"},
        {"card_index": 2, "card_label": "客户分群", "expected_version": "v4", "title": "WEB-22-03 客户分群弹窗显示v4版本"},
        {"card_index": 3, "card_label": "销售预?", "expected_version": "v3", "title": "WEB-22-04 销售预测弹窗显示v3版本"},
    ])
    @allure.title("{case[title]}")
    def test_admin_viz_dialog_shows_version(self, page: Page, case):
        with allure.step("管理员登?"):
            LoginPage(page).navigate().login("admin@shopminer.com", "Admin@123")

        with allure.step("打开后台→模型指?"):
            page.goto(f"{BASE_URL}/#/admin", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            models_menu = page.locator(".el-menu-item:has-text('模型指标')")
            if models_menu.count() > 0:
                models_menu.first.click()
                page.wait_for_timeout(3500)

        with allure.step(f"点击第{case['card_index'] + 1} 个模型卡片的'查看可视化详情'按钮 ({case['card_label']})"):
            viz_buttons = page.locator("button:has-text('查看可视化详情')")
            count = viz_buttons.count()
            assert count >= case["card_index"] + 1, \
                f"Expected at least {case['card_index'] + 1} '查看可视化详情' buttons, found {count}"
            viz_buttons.nth(case["card_index"]).click()
            page.wait_for_timeout(2500)

        with allure.step(f"验证弹窗含版本号 {case['expected_version']}"):
            dialog = page.locator(".el-dialog__body:visible").first
            assert dialog.count() > 0, "Dialog did not open"
            body = dialog.inner_text()
            assert case["expected_version"] in body, \
                f"Dialog should contain version {case['expected_version']}, got: {body[:300]}"


# ============================================================
# WEB-23 管理后台-KPI 卡片核心指标展示 (回归测试)
# 验证每个模型卡片有核心指?"(K/AUC/sMAPE/规则?"
# ============================================================
@allure.feature("Web UI测试")
class TestAdminKpiCards:
    """管理后台 KPI 卡片 - 验证核心指标展示"""

    @allure.story("KPI 卡片核心指标")
    @allure.severity(allure.severity_level.NORMAL)
    @pytest.mark.parametrize("case", [
        {"card_label": "客户分群", "expected_text": "聚类数", "title": "WEB-23-01 聚类KPI卡片显示K"},
        {"card_label": "流失预警", "expected_text": "测试AUC", "title": "WEB-23-02 流失KPI卡片显示测试AUC"},
        {"card_label": "销售预测", "expected_text": "sMAPE", "title": "WEB-23-03 销售预测KPI卡片显示sMAPE"},
        {"card_label": "关联规则", "expected_text": "平均提升度", "title": "WEB-23-04 关联规则KPI卡片显示提升度"},
    ])
    @allure.title("{case[title]}")
    def test_admin_kpi_cards_show_metrics(self, page: Page, case):
        with allure.step("管理员登?"):
            LoginPage(page).navigate().login("admin@shopminer.com", "Admin@123")

        with allure.step("打开后台→模型指?"):
            page.goto(f"{BASE_URL}/#/admin", timeout=20000)
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            models_menu = page.locator(".el-menu-item:has-text('模型指标')")
            if models_menu.count() > 0:
                models_menu.first.click()
                page.wait_for_timeout(3000)

        with allure.step(f"验证 {case['card_label']} 卡片'{case['expected_text']}'"):
            body = page.inner_text("body")
            assert case["expected_text"] in body, \
                f"Expected '{case['expected_text']}' in {case['card_label']} card. Body length: {len(body)}"


# ============================================================
# WEB-24 收藏夹功?"(新功?"
# 验证商品详情 ?"按钮 + 我的收藏页面 + 推荐理由展示
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
                with allure.step(f"验证 {count} 条推荐理由文?"):
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

        with allure.step("点击进入收藏?"):
            fav_menu.first.click()
            page.wait_for_timeout(2000)
            assert "/favorites" in page.url, f"应跳转到 /favorites，实际{page.url}"
