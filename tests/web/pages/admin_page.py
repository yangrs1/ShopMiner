from tests.web.pages.base_page import BasePage


class AdminPage(BasePage):
    # Sidebar menu items
    DASHBOARD_TAB = ".el-menu-item:has-text('数据看板')"
    RFM_TAB = ".el-menu-item:has-text('客户分群')"
    SALES_TAB = ".el-menu-item:has-text('销售分析')"
    ASSOCIATION_TAB = ".el-menu-item:has-text('关联规则')"
    CHURN_TAB = ".el-menu-item:has-text('流失预警')"
    MODELS_TAB = ".el-menu-item:has-text('模型指标')"
    ORDERS_TAB = ".el-menu-item:has-text('订单管理')"
    PRODUCTS_TAB = ".el-menu-item:has-text('商品管理')"
    USERS_TAB = ".el-menu-item:has-text('用户管理')"

    # Sidebar footer
    RECOMPUTE_BUTTON = ".sidebar-footer button:has-text('重新计算')"
    LAST_COMPUTE_TIME = ".compute-time"

    # Admin order management
    ORDER_TABLE = ".el-table"
    SHIP_BUTTON = "button:has-text('发货')"
    REFUND_BUTTON = "button:has-text('退款')"
    DELIVER_BUTTON = "button:has-text('送达')"
    ADMIN_PAY_BUTTON = "button:has-text('付款')"

    # Admin user management
    ADJUST_BALANCE_BUTTON = "button:has-text('调整余额')"
    USER_TABLE = ".el-table"

    # Admin product management
    PRODUCT_SEARCH_INPUT = "input[placeholder='搜索商品名称']"
    PRODUCT_SEARCH_BUTTON = ".toolbar-left button:has-text('搜索')"
    ADD_PRODUCT_BUTTON = "button:has-text('新增商品')"
    PRODUCT_TABLE = ".el-table"

    def __init__(self, page):
        super().__init__(page)

    def navigate(self):
        self.goto("admin")
        self.page.wait_for_load_state("networkidle")
        return self

    def switch_to_tab(self, tab_name):
        """Switch to a sidebar tab by its menu item selector constant."""
        tab_map = {
            "dashboard": self.DASHBOARD_TAB,
            "rfm": self.RFM_TAB,
            "sales": self.SALES_TAB,
            "association": self.ASSOCIATION_TAB,
            "churn": self.CHURN_TAB,
            "models": self.MODELS_TAB,
            "orders": self.ORDERS_TAB,
            "products": self.PRODUCTS_TAB,
            "users": self.USERS_TAB,
        }
        selector = tab_map.get(tab_name)
        if selector:
            self.click(selector)
            self.page.wait_for_load_state("networkidle")
        return self

    def click_recompute(self):
        self.click(self.RECOMPUTE_BUTTON)
        self.wait_for_toast()
        return self

    def get_last_compute_time(self):
        return self.get_text(self.LAST_COMPUTE_TIME)

    # --- Order management sub-actions ---

    def ship_order(self, order_index=0, tracking_number=""):
        """Click the ship button for the given order row and fill tracking number."""
        buttons = self.page.locator(self.SHIP_BUTTON)
        if order_index < buttons.count():
            buttons.nth(order_index).click()
            if tracking_number:
                prompt_input = self.page.locator(".el-message-box .el-input__inner")
                if prompt_input.is_visible():
                    prompt_input.fill(tracking_number)
            self.page.locator(".el-message-box .el-button--primary").click()
            self.wait_for_toast()
            self.page.wait_for_load_state("networkidle")
        return self

    def refund_order(self, order_index=0):
        buttons = self.page.locator(self.REFUND_BUTTON)
        if order_index < buttons.count():
            buttons.nth(order_index).click()
            self.accept_dialog()
            self.wait_for_toast()
            self.page.wait_for_load_state("networkidle")
        return self

    def deliver_order(self, order_index=0):
        buttons = self.page.locator(self.DELIVER_BUTTON)
        if order_index < buttons.count():
            buttons.nth(order_index).click()
            self.wait_for_toast()
            self.page.wait_for_load_state("networkidle")
        return self

    def pay_order_admin(self, order_index=0):
        """Admin pays on behalf of the customer."""
        buttons = self.page.locator(self.ADMIN_PAY_BUTTON)
        if order_index < buttons.count():
            buttons.nth(order_index).click()
            self.accept_dialog()
            self.wait_for_toast()
            self.page.wait_for_load_state("networkidle")
        return self

    # --- User management sub-actions ---

    def adjust_user_balance(self, user_index=0, amount=0):
        buttons = self.page.locator(self.ADJUST_BALANCE_BUTTON)
        if user_index < buttons.count():
            buttons.nth(user_index).click()
            prompt_input = self.page.locator(".el-message-box .el-input__inner")
            if prompt_input.is_visible():
                prompt_input.fill(str(amount))
                self.page.locator(".el-message-box .el-button--primary").click()
                self.wait_for_toast()
                self.page.wait_for_load_state("networkidle")
        return self

    def get_user_row(self, user_index=0):
        """Return the text content of the nth user table row."""
        rows = self.page.locator(self.USER_TABLE).locator(".el-table__body-wrapper tbody tr")
        if user_index < rows.count():
            return rows.nth(user_index).inner_text()
        return ""

    # --- Product management sub-actions ---

    def search_products(self, query):
        self.fill(self.PRODUCT_SEARCH_INPUT, query)
        self.click(self.PRODUCT_SEARCH_BUTTON)
        self.page.wait_for_load_state("networkidle")
        return self

    def click_add_product(self):
        self.click(self.ADD_PRODUCT_BUTTON)
        return self
