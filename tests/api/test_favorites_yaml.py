import allure
import pytest
from tests.utils.yaml_loader import load_yaml


DATA = load_yaml("favorites")


@allure.feature("收藏夹模块")
class TestFavoritesList:

    @allure.story("获取收藏列表")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["favorites_list"])
    def test_list_favorites(self, client, auth_headers, case):
        with allure.step("GET /api/v1/favorites"):
            resp = client.get("/api/v1/favorites", headers=auth_headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if resp.status_code == 200:
            with allure.step("验证响应结构"):
                data = resp.get_json()["data"]
                assert "favorites" in data
                assert "total" in data
                assert isinstance(data["favorites"], list)


@allure.feature("收藏夹模块")
class TestFavoritesAdd:

    @allure.story("添加收藏")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["favorites_add"])
    def test_add_favorite(self, client, auth_headers, app, case):
        payload = case.get("body_override", {"product_id": case.get("product_id")})
        with allure.step(f"POST /api/v1/favorites: {case['name']}"):
            resp = client.post("/api/v1/favorites", headers=auth_headers, json=payload)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case["expected_status"] in (200, 201) and case.get("product_id"):
            with allure.step("DB验证: favorites表新增记录"):
                with app.app_context():
                    from app.models.analytics import Favorite
                    fav = Favorite.query.filter_by(
                        user_id=2, product_id=case["product_id"]
                    ).first()
                    assert fav is not None


@allure.feature("收藏夹模块")
class TestFavoritesRemove:

    @allure.story("取消收藏")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["favorites_remove"])
    def test_remove_favorite(self, client, auth_headers, app, case):
        with allure.step("先添加收藏"):
            client.post(
                "/api/v1/favorites", headers=auth_headers,
                json={"product_id": case["product_id"]},
            )
        with allure.step(f"DELETE /api/v1/favorites/{case['product_id']}"):
            resp = client.delete(
                f"/api/v1/favorites/{case['product_id']}", headers=auth_headers
            )
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        with allure.step("DB验证: favorites表记录已删除"):
            with app.app_context():
                from app.models.analytics import Favorite
                fav = Favorite.query.filter_by(
                    user_id=2, product_id=case["product_id"]
                ).first()
                assert fav is None


@allure.feature("收藏夹模块")
class TestFavoritesCheck:

    @allure.story("检查收藏状态")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["favorites_check"])
    def test_check_favorite(self, client, auth_headers, case):
        with allure.step(f"先添加商品{case['product_id']}到收藏"):
            client.post(
                "/api/v1/favorites", headers=auth_headers,
                json={"product_id": case["product_id"]},
            )
        with allure.step(f"GET /api/v1/favorites/check/{case['product_id']}"):
            resp = client.get(
                f"/api/v1/favorites/check/{case['product_id']}", headers=auth_headers
            )
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if resp.status_code == 200:
            with allure.step("验证返回 favorited=True"):
                assert resp.get_json()["data"]["favorited"] is True


@allure.feature("数据挖掘-推荐理由")
class TestRecommendationReason:

    @allure.story("关联推荐理由")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["favorites_recommendation_reason"])
    def test_recommendation_includes_reason(self, client, case):
        with allure.step(f"GET /api/v1/analytics/association/product/{case['product_id']}"):
            resp = client.get(
                f"/api/v1/analytics/association/product/{case['product_id']}"
            )
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if resp.status_code == 200:
            data = resp.get_json()["data"]
            with allure.step("验证 recommendations 字段是列表"):
                assert isinstance(data["recommendations"], list)
            if data["recommendations"]:
                with allure.step("验证首条推荐包含 reason 字段"):
                    assert "reason" in data["recommendations"][0]
                    assert data["recommendations"][0]["reason"], "reason 不能为空"
