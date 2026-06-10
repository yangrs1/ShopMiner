import allure
import pytest
from tests.utils.yaml_loader import load_yaml

DATA = load_yaml("cart")


@allure.feature("购物车模块")
class TestAddToCart:

    @allure.story("添加商品到购物车")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["add_to_cart"])
    def test_add_to_cart(self, client, auth_headers, app, case):
        if case.get("no_auth"):
            with allure.step("未登录添加商品"):
                resp = client.post("/api/v1/cart", json={
                    "product_id": case["product_id"],
                    "quantity": case["quantity"],
                })
        else:
            if case.get("expected_merged"):
                with allure.step("先添加一次商品"):
                    client.post("/api/v1/cart", headers=auth_headers, json={
                        "product_id": case["product_id"],
                        "quantity": 2,
                    })
            if case.get("pre_add_quantity"):
                with allure.step(f"先添加{case['pre_add_quantity']}件商品"):
                    client.post("/api/v1/cart", headers=auth_headers, json={
                        "product_id": case["product_id"],
                        "quantity": case["pre_add_quantity"],
                    })
            with allure.step(f"添加商品到购物车: {case['name']}"):
                payload = {"quantity": case["quantity"]}
                if case["product_id"] is not None:
                    payload["product_id"] = case["product_id"]
                resp = client.post("/api/v1/cart", headers=auth_headers, json=payload)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case.get("note"):
            allure.attach(case["note"], name="defect_found",
                          attachment_type=allure.attachment_type.TEXT)
        if case.get("expected_merged") and resp.status_code == 200:
            with allure.step("验证合并后数量"):
                data = resp.get_json()["data"]
                item = next((i for i in data if i.get("id") == case["product_id"]), None)
                if item:
                    assert item["quantity"] == 2 + case["quantity"]
        if not case.get("no_auth") and case["expected_status"] == 200 and case.get("product_id") and case["product_id"] not in [None, 99999]:
            with allure.step("DB验证: cart_item表新增记录"):
                with app.app_context():
                    from app.models.order import CartItem
                    item = CartItem.query.filter_by(user_id=2, product_id=case["product_id"]).first()
                    assert item is not None


@allure.feature("购物车模块")
class TestGetCart:

    @allure.story("获取购物车")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("已登录获取购物车")
    def test_get_cart_authenticated(self, client, auth_headers):
        case = DATA["get_cart"][0]
        with allure.step("先添加商品"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
        with allure.step("GET /api/v1/cart"):
            resp = client.get("/api/v1/cart", headers=auth_headers)
            data = resp.get_json()
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case.get("expected_has_items"):
            with allure.step("验证购物车有商品"):
                assert data["data"]["item_count"] >= 1

    @allure.story("获取购物车")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("未登录获取购物车-401")
    def test_get_cart_no_auth(self, client):
        case = DATA["get_cart"][1]
        with allure.step("GET /api/v1/cart(无token)"):
            resp = client.get("/api/v1/cart")
        with allure.step("验证状态码为401"):
            assert resp.status_code == case["expected_status"]


@allure.feature("购物车模块")
class TestUpdateCart:

    @allure.story("更新购物车")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["update_cart"])
    def test_update_cart(self, client, auth_headers, app, case):
        with allure.step("先添加商品"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
        with allure.step(f"PUT /api/v1/cart/{case['product_id']}"):
            resp = client.put(
                f"/api/v1/cart/{case['product_id']}",
                headers=auth_headers,
                json={"quantity": case["quantity"]},
            )
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case["expected_status"] == 200 and case.get("expected_quantity"):
            with allure.step("DB验证: 数量已更新"):
                with app.app_context():
                    from app.models.order import CartItem
                    item = CartItem.query.filter_by(user_id=2, product_id=case["product_id"]).first()
                    assert item.quantity == case["expected_quantity"]


@allure.feature("购物车模块")
class TestRemoveCartItem:

    @allure.story("删除购物车商品")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("删除购物车商品")
    def test_remove_cart_item(self, client, auth_headers, app):
        case = DATA["remove_cart_item"][0]
        with allure.step("先添加商品"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
        with allure.step(f"DELETE /api/v1/cart/{case['product_id']}"):
            resp = client.delete(f"/api/v1/cart/{case['product_id']}", headers=auth_headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        with allure.step("DB验证: cart_item表记录已删除"):
            with app.app_context():
                from app.models.order import CartItem
                item = CartItem.query.filter_by(user_id=2, product_id=case["product_id"]).first()
                assert item is None


@allure.feature("购物车模块")
class TestClearCart:

    @allure.story("清空购物车")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("清空购物车")
    def test_clear_cart(self, client, auth_headers, app):
        case = DATA["clear_cart"][0]
        with allure.step("先添加商品"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
        with allure.step("DELETE /api/v1/cart"):
            resp = client.delete("/api/v1/cart", headers=auth_headers)
            data = resp.get_json()
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case.get("expected_empty"):
            with allure.step("验证购物车为空"):
                assert data["data"] == []
            with allure.step("DB验证: cart_item表该用户记录清空"):
                with app.app_context():
                    from app.models.order import CartItem
                    items = CartItem.query.filter_by(user_id=2).all()
                    assert len(items) == 0
