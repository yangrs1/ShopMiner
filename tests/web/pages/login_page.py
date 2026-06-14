from playwright.sync_api import expect
from tests.web.pages.base_page import BasePage


class LoginPage(BasePage):
    EMAIL_INPUT = "input[placeholder='请输入邮箱']"
    PASSWORD_INPUT = "input[placeholder='请输入密码']"
    LOGIN_BUTTON = "button:has-text('登录')"
    REGISTER_LINK = "a:has-text('立即注册')"
    ERROR_MESSAGE = ".el-message--error"

    def __init__(self, page):
        super().__init__(page)
        self.url = f"{BasePage.url}/#/login"

    def navigate(self):
        self.goto("login")
        self.wait_for_selector(self.EMAIL_INPUT)
        return self

    def login(self, email, password):
        self.fill(self.EMAIL_INPUT, email)
        self.fill(self.PASSWORD_INPUT, password)
        self.click(self.LOGIN_BUTTON)
        self.page.wait_for_timeout(3000)
        # Retry if still on login page (rate limit / failure)
        if "login" in self.page.url:
            self.page.wait_for_timeout(10000)
            self.fill(self.EMAIL_INPUT, email)
            self.fill(self.PASSWORD_INPUT, password)
            self.click(self.LOGIN_BUTTON)
            self.page.wait_for_timeout(3000)
        return self

    def login_success(self, email, password):
        self.login(email, password)
        self.wait_for_toast("登录成功")
        return self

    def login_expect_failure(self, email, password):
        self.login(email, password)
        self.wait_for_toast()
        return self

    def go_to_register(self):
        self.click(self.REGISTER_LINK)
        return self

    def has_error(self):
        return self.is_visible(self.ERROR_MESSAGE)

    def get_error_text(self):
        return self.get_text(self.ERROR_MESSAGE)
