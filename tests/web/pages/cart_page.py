from tests.web.pages.base_page import BasePage


class CartPage(BasePage):
    CART_ITEMS = ".cart-item"
    CHECKOUT_BUTTON = "button:has-text('结算')"
    EMPTY_CART_TEXT = "购物车是空的"
    QUANTITY_INPUT = ".el-input-number .el-input__inner"
    REMOVE_BUTTON = ".cart-item .el-button--danger"
    TOTAL_AMOUNT = ".cart-summary-row .price"
    CART_COUNT = ".cart-badge, .el-badge__content"

    def __init__(self, page):
        super().__init__(page)

    def navigate(self):
        self.goto("cart")
        self.page.wait_for_load_state("networkidle")
        return self

    def get_item_count(self):
        items = self.page.locator(self.CART_ITEMS)
        return items.count()

    def is_empty(self):
        return self.page.locator(f"text={self.EMPTY_CART_TEXT}").is_visible()

    def update_quantity(self, index, quantity):
        inputs = self.page.locator(self.QUANTITY_INPUT)
        if index < inputs.count():
            inputs.nth(index).fill(str(quantity))
            inputs.nth(index).blur()
            self.page.wait_for_load_state("networkidle")
        return self

    def remove_item(self, index=0):
        buttons = self.page.locator(self.REMOVE_BUTTON)
        if index < buttons.count():
            buttons.nth(index).click()
            self.accept_dialog()
            self.page.wait_for_load_state("networkidle")
        return self

    def checkout(self):
        self.click(self.CHECKOUT_BUTTON)
        self.accept_dialog()
        self.wait_for_toast()
        return self

    def get_total_amount(self):
        return self.get_text(self.TOTAL_AMOUNT)
