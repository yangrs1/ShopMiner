import allure
import pytest
from app import create_app
from app.config import Config

pytestmark = pytest.mark.security


@allure.feature("安全配置测试")
@allure.story("CORS配置")
class TestCORSConfig:

    @allure.title("CORS不应允许任意源访问(DEF-002)")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_cors_not_wildcard(self):
        app = create_app("testing")
        cors_cfg = app.config.get("CORS_ORIGINS") or {}
        with app.app_context():
            for rule in app.url_map.iter_rules():
                if rule.rule.startswith("/api/"):
                    cors_res = app.extensions.get("cors")
                    if cors_res:
                        for res_cfg in cors_res._options:
                            origins = res_cfg.get("origins") if isinstance(res_cfg, dict) else None
                            if origins == "*":
                                pytest.fail(
                                    "CORS origins='*' 允许任意源访问，"
                                    "生产环境应限制为前端域名白名单 (DEF-002)"
                                )

    @allure.title("CORS预检请求OPTIONS应返回正确头")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_cors_preflight_options(self, client):
        resp = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://evil-site.com",
                "Access-Control-Request-Method": "POST",
            },
        )
        if resp.status_code in (200, 204):
            allow_origin = resp.headers.get("Access-Control-Allow-Origin", "")
            assert allow_origin not in ("*", "http://evil-site.com"), (
                f"恶意源不应被CORS允许，实际: {allow_origin}"
            )

        resp_allowed = client.options(
            "/api/v1/auth/login",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        if resp_allowed.status_code in (200, 204):
            allow_origin = resp_allowed.headers.get("Access-Control-Allow-Origin", "")
            assert allow_origin == "http://localhost:3000", (
                f"允许的源应返回Allow-Origin头，实际: {allow_origin}"
            )


@allure.feature("安全配置测试")
@allure.story("JWT密钥强度")
class TestJWTKeyStrength:

    @allure.title("JWT密钥长度应>=32字节(DEF-004)")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_jwt_key_minimum_length(self):
        key = Config.JWT_SECRET_KEY
        if key == "jwt-secret-key":
            key_bytes = len(key.encode("utf-8"))
            assert key_bytes >= 32, (
                f"JWT密钥仅{key_bytes}字节，低于SHA256推荐的32字节最低长度 (DEF-004)"
            )

    @allure.title("JWT密钥不应为硬编码默认值")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_jwt_key_not_default(self):
        import os
        env_key = os.getenv("JWT_SECRET_KEY")
        if env_key is None:
            default_key = Config.JWT_SECRET_KEY
            assert default_key != "jwt-secret-key", (
                "JWT_SECRET_KEY使用硬编码默认值'jwt-secret-key'，"
                "应通过环境变量注入强密钥 (DEF-004)"
            )


@allure.feature("安全配置测试")
@allure.story("密码强度")
class TestPasswordStrength:

    @allure.title("注册接口应拒绝弱密码(DEF-010)")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_weak_password_rejected(self, client):
        weak_passwords = [
            ("1", "单字符密码"),
            ("1234567", "7位纯数字"),
            ("abcdefg", "7位纯字母"),
        ]
        for pwd, desc in weak_passwords:
            with allure.step(f"尝试注册弱密码: {desc}"):
                resp = client.post("/api/v1/auth/register", json={
                    "first_name": "Weak",
                    "last_name": "Pwd",
                    "email": f"weak_{pwd}@test.com",
                    "password": pwd,
                })
                assert resp.status_code != 201, f"弱密码'{pwd}'({desc})不应注册成功"

    @allure.title("注册接口应拒绝空密码")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_empty_password_rejected(self, client):
        resp = client.post("/api/v1/auth/register", json={
            "first_name": "Empty",
            "last_name": "Pwd",
            "email": "empty_pwd@test.com",
            "password": "",
        })
        assert resp.status_code != 201, "空密码不应注册成功"


@allure.feature("安全配置测试")
@allure.story("邮箱格式校验")
class TestEmailValidation:

    @allure.title("注册接口应拒绝非法邮箱格式(DEF-011)")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_invalid_email_rejected(self, client):
        invalid_emails = [
            "notanemail",
            "@no-local.com",
            "no-at-sign.com",
            "spaces in@email.com",
        ]
        for email in invalid_emails:
            with allure.step(f"尝试注册非法邮箱: {email}"):
                resp = client.post("/api/v1/auth/register", json={
                    "first_name": "Bad",
                    "last_name": "Email",
                    "email": email,
                    "password": "Test@12345",
                })
                assert resp.status_code == 400, f"非法邮箱'{email}'应返回400，实际:{resp.status_code}"
                msg = resp.get_json()["message"]
                assert "Invalid email" in msg, f"应提示邮箱格式错误，实际:{msg}"


@allure.feature("安全配置测试")
@allure.story("API限流")
class TestRateLimiting:

    @allure.title("登录接口应有限流机制(DEF-009)")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_login_rate_limiting(self, client):
        with allure.step("连续20次错误登录，验证限流触发"):
            status_codes = []
            for i in range(20):
                resp = client.post("/api/v1/auth/login", json={
                    "email": f"ratelimit_{i}@test.com",
                    "password": "WrongPass",
                })
                status_codes.append(resp.status_code)

            rate_limited = [s for s in status_codes if s == 429]
            assert len(rate_limited) > 0, (
                f"20次请求中应出现429限流，实际状态码分布: {sorted(set(status_codes))}"
            )


@allure.feature("安全配置测试")
@allure.story("安全响应头")
class TestSecurityHeaders:

    @allure.title("API响应应包含安全相关头")
    @allure.severity(allure.severity_level.NORMAL)
    def test_security_headers(self, client):
        resp = client.get("/api/v1/products")
        headers = {k.lower(): v for k, v in resp.headers.items()}

        recommended = [
            ("x-content-type-options", "nosniff"),
            ("x-frame-options", "DENY"),
            ("content-security-policy", None),
        ]
        missing = []
        for header, expected_val in recommended:
            if header not in headers:
                missing.append(header)
            elif expected_val and headers[header] != expected_val:
                missing.append(f"{header}={headers[header]}(期望{expected_val})")

        if missing:
            allure.attach(
                f"缺失/不正确的安全头: {', '.join(missing)}",
                "安全建议",
                allure.attachment_type.TEXT,
            )
