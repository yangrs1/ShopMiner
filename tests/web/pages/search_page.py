from playwright.sync_api import expect
from tests.web.pages.base_page import BasePage


class SearchPage(BasePage):
    SEARCH_INPUT = "input[placeholder*='搜索']"
    SEARCH_RESULTS = ".product-card"
    EMPTY_RESULT = "text=未找到相关商品"
    PAGE_TITLE = ".page-title"

    # Filter bar
    MIN_PRICE_INPUT = "input[placeholder='最低价']"
    MAX_PRICE_INPUT = "input[placeholder='最高价']"
    CATEGORY_SELECT = ".filter-select:has(.el-select__placeholder:text('品类'))"
    SORT_SELECT = ".filter-select:has(.el-select__placeholder:text('排序'))"
    RESET_BUTTON = "button:has-text('重置')"

    def __init__(self, page):
        super().__init__(page)

    def navigate(self, query=""):
        if query:
            self.goto(f"search?q={query}")
        else:
            self.goto("search")
        self.page.wait_for_load_state("networkidle")
        return self

    def search(self, query):
        """Fill the navbar search input and press Enter to trigger search navigation."""
        inp = self.page.locator(self.SEARCH_INPUT).first
        inp.fill(query)
        inp.press("Enter")
        self.page.wait_for_load_state("networkidle")
        return self

    def get_result_count(self):
        return self.page.locator(self.SEARCH_RESULTS).count()

    def has_results(self):
        return self.get_result_count() > 0

    def filter_by_category(self, category_name):
        """Select a category from the category filter dropdown."""
        self.click(self.CATEGORY_SELECT)
        option = self.page.locator(f".el-select-dropdown__item:has-text('{category_name}')")
        if option.is_visible():
            option.click()
            self.page.wait_for_load_state("networkidle")
        return self

    def sort_by_price(self, order="asc"):
        """Sort by price. order='asc' for ascending, 'desc' for descending."""
        self.click(self.SORT_SELECT)
        label = "价格 ↑" if order == "asc" else "价格 ↓"
        option = self.page.locator(f".el-select-dropdown__item:has-text('{label}')")
        if option.is_visible():
            option.click()
            self.page.wait_for_load_state("networkidle")
        return self

    def sort_by(self, label):
        """Sort by the given option label text (综合排序, 价格 ↑, 价格 ↓, 评分 ↓, 最新)."""
        self.click(self.SORT_SELECT)
        option = self.page.locator(f".el-select-dropdown__item:has-text('{label}')")
        if option.is_visible():
            option.click()
            self.page.wait_for_load_state("networkidle")
        return self

    def click_result(self, index=0):
        results = self.page.locator(self.SEARCH_RESULTS)
        if index < results.count():
            results.nth(index).click()
            self.page.wait_for_load_state("networkidle")
        return self

    def reset_filters(self):
        self.click(self.RESET_BUTTON)
        self.page.wait_for_load_state("networkidle")
        return self
