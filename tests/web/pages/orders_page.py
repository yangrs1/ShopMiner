from tests.web.pages.base_page import BasePage


class OrdersPage(BasePage):
    ORDER_ITEMS = ".order-item"
    EMPTY_ORDERS_TEXT = "暂无订单"
    ORDER_STATUS_TAG = ".order-header .el-tag"
    ORDER_DETAIL_LINK = ".order-footer button:has-text('查看详情')"
    CANCEL_BUTTON = ".order-footer button:has-text('取消订单')"
    PAY_BUTTON = ".order-footer button:has-text('付款')"
    ORDER_TOTAL = ".order-footer .price"
    ORDER_ID = ".order-id"

    def __init__(self, page):
        super().__init__(page)

    def navigate(self):
        self.goto("orders")
        self.page.wait_for_load_state("networkidle")
        return self

    def get_order_count(self):
        return self.page.locator(self.ORDER_ITEMS).count()

    def has_orders(self):
        return self.get_order_count() > 0

    def view_order_detail(self, index=0):
        buttons = self.page.locator(self.ORDER_DETAIL_LINK)
        if index < buttons.count():
            buttons.nth(index).click()
            self.page.wait_for_load_state("networkidle")
        return self

    def cancel_order(self, index=0):
        buttons = self.page.locator(self.CANCEL_BUTTON)
        if index < buttons.count():
            buttons.nth(index).click()
            self.accept_dialog()
            self.wait_for_toast()
            self.page.wait_for_load_state("networkidle")
        return self

    def pay_order(self, index=0):
        buttons = self.page.locator(self.PAY_BUTTON)
        if index < buttons.count():
            buttons.nth(index).click()
            self.accept_dialog()
            self.wait_for_toast()
            self.page.wait_for_load_state("networkidle")
        return self

    def confirm_receipt(self, index=0):
        """Navigate to order detail and confirm receipt."""
        self.view_order_detail(index)
        confirm_btn = self.page.locator("button:has-text('确认收货')")
        if confirm_btn.is_visible():
            confirm_btn.click()
            self.accept_dialog()
            self.wait_for_toast()
            self.page.wait_for_load_state("networkidle")
        return self

    def get_order_status(self, index=0):
        tags = self.page.locator(self.ORDER_STATUS_TAG)
        if index < tags.count():
            return tags.nth(index).inner_text() or ""
        return ""

    def get_total_amount(self, index=0):
        totals = self.page.locator(self.ORDER_TOTAL)
        if index < totals.count():
            return totals.nth(index).inner_text() or ""
        return ""
