import allure
import pytest
from tests.utils.yaml_loader import load_yaml

DATA = load_yaml("auth")


@allure.feature("认证模块")
class TestRegister:

    @allure.story("注册成功")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["register_success"])
    def test_register_success(self, client, app, case):
        with allure.step(f"发送注册请求: {case['email']}"):
            resp = client.post("/api/v1/auth/register", json={
                "first_name": case["first_name"],
                "last_name": case["last_name"],
                "email": case["email"],
                "password": case["password"],
                "address": case.get("address", ""),
            })
            data = resp.get_json()
        with allure.step("验证HTTP状态码"):
            assert resp.status_code == case["expected_status"]
        with allure.step("验证业务码"):
            assert data["code"] == case["expected_code"]
        with allure.step("验证返回access_token"):
            assert "access_token" in data["data"]
        with allure.step("DB验证: user表新增记录"):
            with app.app_context():
                from app.models.user import User
                user = User.query.filter_by(email=case["email"]).first()
                assert user is not None

    @allure.story("注册失败-缺少字段")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["register_missing_fields"])
    def test_register_missing_fields(self, client, case):
        if case.get("empty_body"):
            with allure.step("发送空请求体注册"):
                resp = client.post("/api/v1/auth/register")
        else:
            with allure.step(f"发送注册请求(缺少字段): {case['name']}"):
                resp = client.post("/api/v1/auth/register", json={
                    "first_name": case.get("first_name", ""),
                    "last_name": case.get("last_name", ""),
                    "email": case.get("email", ""),
                    "password": case.get("password", ""),
                })
        with allure.step("验证状态码为400"):
            assert resp.status_code == case["expected_status"]

    @allure.story("注册失败-重复邮箱")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["register_duplicate"])
    def test_register_duplicate_email(self, client, case):
        with allure.step(f"发送重复邮箱注册: {case['email']}"):
            resp = client.post("/api/v1/auth/register", json={
                "first_name": case["first_name"],
                "last_name": case["last_name"],
                "email": case["email"],
                "password": case["password"],
            })
        with allure.step("验证状态码为409"):
            assert resp.status_code == case["expected_status"]


@allure.feature("认证模块")
class TestLogin:

    @allure.story("登录成功")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["login_success"])
    def test_login_success(self, client, case):
        with allure.step(f"发送登录请求: {case['email']}"):
            resp = client.post("/api/v1/auth/login", json={
                "email": case["email"],
                "password": case["password"],
            })
            data = resp.get_json()
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        with allure.step("验证返回access_token"):
            assert "access_token" in data["data"]

    @allure.story("登录失败")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["login_failure"])
    def test_login_failure(self, client, case):
        if case.get("empty_body"):
            with allure.step("发送空请求体登录"):
                resp = client.post("/api/v1/auth/login")
        else:
            with allure.step(f"发送登录请求(期望失败): {case['name']}"):
                resp = client.post("/api/v1/auth/login", json={
                    "email": case["email"],
                    "password": case["password"],
                })
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("认证模块")
class TestGetCurrentUser:

    @allure.story("获取当前用户")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("已登录用户获取信息")
    def test_get_current_user_authenticated(self, client, auth_headers):
        case = DATA["get_current_user"][0]
        with allure.step("发送GET /api/v1/auth/me"):
            resp = client.get("/api/v1/auth/me", headers=auth_headers)
            data = resp.get_json()
        with allure.step("验证状态码和邮箱"):
            assert resp.status_code == case["expected_status"]
            assert data["data"]["email"] == case["expected_email"]

    @allure.story("获取当前用户")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("未登录获取信息-401")
    def test_get_current_user_no_token(self, client):
        case = DATA["get_current_user"][1]
        with allure.step("发送GET /api/v1/auth/me(无token)"):
            resp = client.get("/api/v1/auth/me")
        with allure.step("验证状态码为401"):
            assert resp.status_code == case["expected_status"]


@allure.feature("认证模块")
class TestUpdateUser:

    @allure.story("更新用户信息")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA.get("update_user", []))
    def test_update_user(self, client, auth_headers, app, case):
        with allure.step(f"发送PUT /api/v1/auth/me: {case['name']}"):
            payload = {}
            if "first_name" in case:
                payload["first_name"] = case["first_name"]
            if "address" in case:
                payload["address"] = case["address"]
            if "password" in case:
                payload["password"] = case["password"]
            resp = client.put("/api/v1/auth/me", headers=auth_headers, json=payload)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case.get("expected_field") and resp.status_code == 200:
            with allure.step(f"DB验证: {case['expected_field']}已更新"):
                with app.app_context():
                    from app.models.user import User
                    user = User.query.filter_by(email="customer@shopminer.com").first()
                    assert getattr(user, case["expected_field"]) == case["expected_value"]


@allure.feature("认证模块")
class TestRecharge:

    @allure.story("充值")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA.get("recharge", []))
    def test_recharge(self, client, auth_headers, app, case):
        with app.app_context():
            from app.models.user import User
            user_before = User.query.filter_by(email="customer@shopminer.com").first()
            balance_before = user_before.balance

        with allure.step(f"发送充值请求: amount={case['amount']}"):
            resp = client.post("/api/v1/auth/me/recharge", headers=auth_headers, json={
                "amount": case["amount"],
            })
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]

        if case["expected_status"] == 200 and case.get("expected_balance_increase"):
            with allure.step("DB验证: 余额已增加"):
                with app.app_context():
                    user_after = User.query.filter_by(email="customer@shopminer.com").first()
                    assert user_after.balance == balance_before + case["expected_balance_increase"]
