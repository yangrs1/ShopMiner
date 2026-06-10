import os
from playwright.sync_api import Page, expect


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")


class BasePage:
    url = BASE_URL

    def __init__(self, page: Page):
        self.page = page

    def goto(self, path=""):
        self.page.goto(f"{self.url}/#{path}")
        self.page.wait_for_load_state("networkidle")
        return self

    def wait_for_url(self, path_fragment, timeout=10000):
        self.page.wait_for_url(f"**#{path_fragment}**", timeout=timeout)
        return self

    def click(self, selector):
        self.page.click(selector)
        return self

    def fill(self, selector, value):
        self.page.fill(selector, value)
        return self

    def get_text(self, selector):
        return self.page.text_content(selector) or ""

    def is_visible(self, selector):
        return self.page.is_visible(selector)

    def wait_for_selector(self, selector, timeout=10000):
        self.page.wait_for_selector(selector, timeout=timeout)
        return self

    def screenshot(self, path):
        self.page.screenshot(path=path, full_page=True)
        return self

    def get_current_url(self):
        return self.page.url

    def wait_for_toast(self, text=None, timeout=5000):
        if text:
            self.page.locator(f".el-message:has-text('{text}')").first.wait_for(state="visible", timeout=timeout)
        else:
            self.page.locator(".el-message").first.wait_for(state="visible", timeout=timeout)
        return self

    def accept_dialog(self):
        self.page.locator(".el-message-box .el-button--primary").click()
        return self
