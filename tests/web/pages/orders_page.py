from tests.web.pages.base_page import BasePage


class OrdersPage(BasePage):
    ORDER_ITEMS = ".order-item, .order-card"
    EMPTY_ORDERS_TEXT = "暂无订单"

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
