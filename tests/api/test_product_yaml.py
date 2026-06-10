import allure
import pytest
from app.extensions import db
from tests.utils.yaml_loader import load_yaml

DATA = load_yaml("product")


@allure.feature("商品模块")
class TestGetProducts:

    @allure.story("获取商品列表")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["get_products"])
    def test_get_products(self, client, case):
        with allure.step(f"GET /api/v1/products: {case['name']}"):
            resp = client.get("/api/v1/products", query_string=case.get("params", {}))
            data = resp.get_json()
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case.get("expected_has_products"):
            with allure.step("验证商品列表非空"):
                assert len(data["data"]["products"]) > 0
        if case.get("expected_type"):
            with allure.step(f"验证商品类型为{case['expected_type']}"):
                for p in data["data"]["products"]:
                    assert p["type"] == case["expected_type"]
        if case.get("expected_max_items"):
            with allure.step(f"验证商品数<={case['expected_max_items']}"):
                assert len(data["data"]["products"]) <= case["expected_max_items"]


@allure.feature("商品模块")
class TestGetCategories:

    @allure.story("获取分类列表")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("获取分类列表")
    def test_get_categories(self, client):
        case = DATA["get_categories"][0]
        with allure.step("GET /api/v1/products/categories"):
            resp = client.get("/api/v1/products/categories")
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("商品模块")
class TestGetProductDetail:

    @allure.story("获取商品详情")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["get_product_detail"])
    def test_get_product_detail(self, client, case):
        with allure.step(f"GET /api/v1/products/{case['product_id']}"):
            resp = client.get(f"/api/v1/products/{case['product_id']}")
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("商品模块")
class TestCreateProduct:

    @allure.story("创建商品")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["create_product"])
    def test_create_product(self, client, auth_headers, admin_headers, app, case):
        headers = admin_headers if case["as_admin"] else auth_headers
        with allure.step(f"POST /api/v1/products: {case['name']}"):
            resp = client.post("/api/v1/products", headers=headers, json={
                "name": case["name"],
                "description": case["description"],
                "image": case["image"],
                "price": case["price"],
                "stock": case["stock"],
                "type": case["type"],
                "category_name": case.get("category_name", ""),
            })
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case.get("note"):
            allure.attach(case["note"], name="defect_found",
                          attachment_type=allure.attachment_type.TEXT)
        if case["expected_status"] == 201 and not case.get("note"):
            with allure.step("DB验证: product表新增记录"):
                with app.app_context():
                    from app.models.product import Product
                    p = Product.query.filter_by(name=case["name"]).first()
                    assert p is not None


@allure.feature("商品模块")
class TestUpdateProduct:

    @allure.story("更新商品")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["update_product"])
    def test_update_product(self, client, admin_headers, app, case):
        with allure.step(f"PUT /api/v1/products/{case['product_id']}"):
            resp = client.put(
                f"/api/v1/products/{case['product_id']}",
                headers=admin_headers,
                json=case["data"],
            )
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case["expected_status"] == 200:
            with allure.step("DB验证: product表字段已更新"):
                with app.app_context():
                    from app.models.product import Product
                    p = db.session.get(Product, case["product_id"])
                    for k, v in case["data"].items():
                        assert getattr(p, k) == v


@allure.feature("商品模块")
class TestDeleteProduct:

    @allure.story("下架商品")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["delete_product"])
    def test_delete_product(self, client, auth_headers, admin_headers, app, case):
        headers = admin_headers if case["as_admin"] else auth_headers
        with allure.step(f"DELETE /api/v1/products/{case['product_id']}"):
            resp = client.delete(
                f"/api/v1/products/{case['product_id']}",
                headers=headers,
            )
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case["as_admin"] and case["expected_status"] == 200:
            with allure.step("DB验证: product表is_active=False"):
                with app.app_context():
                    from app.models.product import Product
                    p = db.session.get(Product, case["product_id"])
                    assert p.is_active is False
