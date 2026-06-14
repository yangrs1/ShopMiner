from tests.web.pages.base_page import BasePage


class FavoritesPage(BasePage):
    FAVORITE_ITEMS = ".fav-item"
    EMPTY_FAVORITES = "text=还没有收藏任何商品"
    REMOVE_BUTTON = ".fav-actions button:has-text('取消收藏')"
    ADD_TO_CART_BUTTON = ".fav-item .product-card button:has-text('加入购物车')"
    FAVORITE_COUNT = ".fav-count"

    def __init__(self, page):
        super().__init__(page)

    def navigate(self):
        self.goto("favorites")
        self.page.wait_for_load_state("networkidle")
        return self

    def get_favorite_count(self):
        return self.page.locator(self.FAVORITE_ITEMS).count()

    def has_favorites(self):
        return self.get_favorite_count() > 0

    def remove_favorite(self, index=0):
        buttons = self.page.locator(self.REMOVE_BUTTON)
        if index < buttons.count():
            buttons.nth(index).click()
            self.accept_dialog()
            self.wait_for_toast()
            self.page.wait_for_load_state("networkidle")
        return self

    def add_to_cart_from_favorites(self, index=0):
        buttons = self.page.locator(self.ADD_TO_CART_BUTTON)
        if index < buttons.count():
            buttons.nth(index).click()
            self.wait_for_toast()
            self.page.wait_for_load_state("networkidle")
        return self
