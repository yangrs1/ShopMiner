from tests.web.pages.base_page import BasePage


class HomePage(BasePage):
    PRODUCT_CARDS = ".product-card, .el-card"
    CATEGORY_NAV = ".category-nav"
    EXPLORE_BUTTON = "button:has-text('探索商品')"
    PRODUCT_LINK = ".product-card a, .el-card a"

    def __init__(self, page):
        super().__init__(page)
        self.url = f"{BasePage.url}/#/"

    def navigate(self):
        self.goto("")
        self.page.wait_for_load_state("networkidle")
        return self

    def has_products(self):
        cards = self.page.locator(self.PRODUCT_CARDS)
        return cards.count() > 0

    def get_product_count(self):
        cards = self.page.locator(self.PRODUCT_CARDS)
        return cards.count()

    def click_explore(self):
        self.click(self.EXPLORE_BUTTON)
        return self

    def select_category(self, category_name):
        cat_link = self.page.locator(f".category-nav >> text='{category_name}'")
        cat_link.first.click()
        self.page.wait_for_load_state("networkidle")
        return self

    def click_first_product(self):
        first_link = self.page.locator(self.PRODUCT_LINK).first
        first_link.click()
        self.page.wait_for_load_state("networkidle")
        return self
