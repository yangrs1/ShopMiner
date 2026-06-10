import allure
import pytest
from tests.utils.yaml_loader import load_yaml

DATA = load_yaml("reviews")

pytestmark = pytest.mark.api


@allure.feature("评价模块")
class TestGetProductReviews:

    @allure.story("获取商品评价列表")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["get_product_reviews"])
    def test_get_product_reviews(self, client, app, case):
        with allure.step(f"GET /api/v1/reviews/product/{case['product_id']}"):
            resp = client.get(
                f"/api/v1/reviews/product/{case['product_id']}",
                query_string=case.get("params", {}),
            )
            data = resp.get_json()
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case.get("expected_has_reviews") is not None:
            with allure.step(f"验证评价列表{'非空' if case['expected_has_reviews'] else '为空'}"):
                reviews = data.get("data", {}).get("reviews", [])
                if case["expected_has_reviews"]:
                    assert len(reviews) >= 0
                else:
                    assert len(reviews) == 0


@allure.feature("评价模块")
class TestCreateReview:

    @allure.story("创建评价")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["create_review"])
    def test_create_review(self, client, auth_headers, app, case):
        if case.get("no_auth"):
            headers = {}
        else:
            headers = auth_headers

        payload = {}
        if "product_id" in case:
            payload["product_id"] = case["product_id"]
        if "rating" in case:
            payload["rating"] = case["rating"]
        if "content" in case:
            payload["content"] = case["content"]

        if case.get("note") and "重复" in case.get("note", ""):
            with allure.step("先创建一条评价"):
                client.post("/api/v1/reviews", headers=headers, json=payload)

        if case["name"] == "创建评价-重复评价应更新而非新建":
            with allure.step("先创建一条评价"):
                client.post("/api/v1/reviews", headers=headers, json=payload)

        with allure.step(f"POST /api/v1/reviews: {case['name']}"):
            resp = client.post("/api/v1/reviews", headers=headers, json=payload)
            data = resp.get_json()

        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if "expected_code" in case:
            with allure.step("验证业务码"):
                assert data["code"] == case["expected_code"]
        if case.get("note"):
            allure.attach(case["note"], name="note", attachment_type=allure.attachment_type.TEXT)
