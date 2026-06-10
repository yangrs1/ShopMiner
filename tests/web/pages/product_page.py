from tests.web.pages.base_page import BasePage


class ProductDetailPage(BasePage):
    PRODUCT_NAME = ".product-detail h2, .product-detail h1, .page-card h2"
    ADD_TO_CART_BUTTON = "button:has-text('加入购物车')"
    PRICE_TEXT = ".price"
    RECOMMENDATION_SECTION = ".recommendation, .related-products"

    def __init__(self, page):
        super().__init__(page)

    def navigate(self, product_id):
        self.goto(f"product/{product_id}")
        self.page.wait_for_load_state("networkidle")
        return self

    def get_product_name(self):
        return self.get_text(self.PRODUCT_NAME)

    def add_to_cart(self):
        self.click(self.ADD_TO_CART_BUTTON)
        self.wait_for_toast()
        return self

    def has_recommendations(self):
        return self.is_visible(self.RECOMMENDATION_SECTION)
