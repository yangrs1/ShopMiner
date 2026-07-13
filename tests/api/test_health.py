"""Tests for health check endpoint."""
import allure


@allure.feature("系统健康检查")
class TestHealthCheck:

    @allure.story("健康检查接口")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("GET /api/v1/health → 200 + 标准响应结构")
    def test_health_check(self, client):
        # [GAP: missing-test]
        with allure.step("GET /api/v1/health"):
            resp = client.get("/api/v1/health")

        with allure.step("验证状态码为200"):
            assert resp.status_code == 200

        data = resp.get_json()
        with allure.step("验证响应包含status字段"):
            assert "status" in data
            assert data["status"] in ("healthy", "degraded")

        with allure.step("验证响应包含timestamp字段"):
            assert "timestamp" in data

        with allure.step("验证响应包含version字段"):
            assert "version" in data
            assert data["version"] == "1.0.0"

        with allure.step("验证响应包含database字段"):
            assert "database" in data
            assert data["database"] in ("connected", "disconnected")
