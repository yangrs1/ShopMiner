from tests.web.pages.base_page import BasePage


class ProfilePage(BasePage):
    PROFILE_INFO = ".profile-page"
    RFM_SECTION = ".rfm-section, .analytics-card"
    CONSUMPTION_CHART = "canvas"
    PHONE_INPUT = "input[placeholder='请输入手机号']"
    ADDRESS_INPUT = "input[placeholder='请输入收货地址']"
    PASSWORD_INPUT = "input[placeholder='留空则不修改']"
    SAVE_BUTTON = "button:has-text('保存修改')"
    RECHARGE_BUTTON = "button:has-text('充值')"
    RFM_SEGMENT_TAG = ".segment-info .el-tag"
    BALANCE_TAG = ".el-form-item:has(.el-form-item__label:text('余额')) .el-tag"
    EMAIL_INPUT = ".el-form-item:has(.el-form-item__label:text('邮箱')) input"
    SEGMENT_ADVICE = ".segment-advice"

    def __init__(self, page):
        super().__init__(page)

    def navigate(self):
        self.goto("profile")
        self.page.wait_for_load_state("networkidle")
        return self

    def has_profile_info(self):
        return self.is_visible(self.PROFILE_INFO)

    def has_rfm_section(self):
        return self.is_visible(self.RFM_SECTION)

    def has_charts(self):
        return self.is_visible(self.CONSUMPTION_CHART)

    def get_rfm_segment(self):
        if self.is_visible(self.RFM_SEGMENT_TAG):
            return self.get_text(self.RFM_SEGMENT_TAG)
        return ""

    def get_user_email(self):
        return self.page.input_value(self.EMAIL_INPUT) or ""

    def get_balance(self):
        text = self.get_text(self.BALANCE_TAG)
        return text.strip()

    def get_user_name(self):
        """Get the display name from the navbar user menu."""
        name_el = self.page.locator(".el-sub-menu .el-sub-menu__title")
        if name_el.count() > 0:
            return name_el.first.inner_text().strip()
        return ""

    def edit_profile(self, data: dict):
        """Update profile fields. Accepted keys: phone, address, password."""
        if "phone" in data:
            self.fill(self.PHONE_INPUT, data["phone"])
        if "address" in data:
            self.fill(self.ADDRESS_INPUT, data["address"])
        if "password" in data:
            self.fill(self.PASSWORD_INPUT, data["password"])
        self.click(self.SAVE_BUTTON)
        self.wait_for_toast()
        return self

    def recharge(self, amount: str):
        """Click recharge and fill the prompt dialog."""
        self.click(self.RECHARGE_BUTTON)
        prompt_input = self.page.locator(".el-message-box .el-input__inner")
        if prompt_input.is_visible():
            prompt_input.fill(amount)
            self.page.locator(".el-message-box .el-button--primary").click()
            self.wait_for_toast()
            self.page.wait_for_load_state("networkidle")
        return self

    def get_segment_advice(self):
        if self.is_visible(self.SEGMENT_ADVICE):
            return self.get_text(self.SEGMENT_ADVICE)
        return ""
