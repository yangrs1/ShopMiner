from tests.web.pages.base_page import BasePage


class ProfilePage(BasePage):
    PROFILE_INFO = ".profile-info, .user-info"
    RFM_SECTION = ".rfm-section, .analytics-card"
    CONSUMPTION_CHART = ".chart-container, canvas"

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
