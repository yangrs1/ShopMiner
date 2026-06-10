from tests.web.pages.base_page import BasePage


class RegisterPage(BasePage):
    FIRST_NAME_INPUT = "input[placeholder='请输入名']"
    LAST_NAME_INPUT = "input[placeholder='请输入姓']"
    EMAIL_INPUT = "input[placeholder='请输入邮箱']"
    PASSWORD_INPUT = "input[placeholder='至少6位，含大小写和数字']"
    ADDRESS_INPUT = "input[placeholder='请输入收货地址']"
    REGISTER_BUTTON = "button:has-text('注册')"
    LOGIN_LINK = "a:has-text('去登录')"

    def __init__(self, page):
        super().__init__(page)
        self.url = f"{BasePage.url}/#/register"

    def navigate(self):
        self.goto("register")
        self.wait_for_selector(self.FIRST_NAME_INPUT)
        return self

    def register(self, first_name, last_name, email, password, address=""):
        self.fill(self.LAST_NAME_INPUT, last_name)
        self.fill(self.FIRST_NAME_INPUT, first_name)
        self.fill(self.EMAIL_INPUT, email)
        self.fill(self.PASSWORD_INPUT, password)
        if address:
            self.fill(self.ADDRESS_INPUT, address)
        self.click(self.REGISTER_BUTTON)
        return self

    def register_success(self, first_name, last_name, email, password, address=""):
        self.register(first_name, last_name, email, password, address)
        self.wait_for_toast("注册成功")
        return self

    def go_to_login(self):
        self.click(self.LOGIN_LINK)
        return self
