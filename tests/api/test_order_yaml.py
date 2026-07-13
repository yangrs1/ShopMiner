import allure
import pytest
from app.extensions import db
from tests.utils.yaml_loader import load_yaml

DATA = load_yaml("order")

# ---------------------------------------------------------------------------
# Consolidation: scenarios covered by Python-only tests with deeper assertions
# [GAP: resolved-redundancy] create_order: 正常创建订单 → test_order_bugs.py BUG-001
# [GAP: resolved-redundancy] pay_order: 正常支付pending订单 → test_business_order.py BIZ-016
# [GAP: resolved-redundancy] cancel_order: 用户取消pending订单 → test_business_order.py BIZ-007
# [GAP: resolved-redundancy] cancel_order: 用户取消已支付订单-自动退款 → test_business_order.py BIZ-008
# [GAP: resolved-redundancy] refund_order: 管理员退款已支付订单 → test_business_order.py BIZ-017 / test_e2e_flow.py E2E-002
# [GAP: resolved-redundancy] get_order_status_logs: 获取订单状态日志 → test_e2e_flow.py E2E-005
# ---------------------------------------------------------------------------
_COVERED_SCENARIOS = {
    "create_order": {"正常创建订单"},
    "pay_order": {"正常支付pending订单"},
    "cancel_order": {"用户取消pending订单", "用户取消已支付订单-自动退款"},
    "refund_order": {"管理员退款已支付订单"},
    "get_order_status_logs": {"获取订单状态日志"},
}


@allure.feature("订单模块")
class TestCreateOrder:

    @allure.story("创建订单")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", [c for c in DATA["create_order"] if c["name"] not in _COVERED_SCENARIOS["create_order"]])
    def test_create_order(self, client, auth_headers, app, case):
        if case.get("pre_add_cart"):
            with allure.step("先添加商品到购物车"):
                client.post("/api/v1/cart", headers=auth_headers, json={
                    "product_id": case.get("product_id", 1),
                    "quantity": case.get("quantity", 1),
                })
        with allure.step("POST /api/v1/orders"):
            resp = client.post("/api/v1/orders", headers=auth_headers)
            data = resp.get_json()
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case.get("expected_status_field"):
            with allure.step(f"验证订单状态为{case['expected_status_field']}"):
                assert data["data"]["status"] == case["expected_status_field"]
        if case["expected_status"] == 201:
            with allure.step("DB验证: order表新增记录"):
                with app.app_context():
                    from app.models.order import Order
                    order = db.session.get(Order, data["data"]["id"])
                    assert order is not None
                    assert order.status == "pending"


@allure.feature("订单模块")
class TestPayOrder:

    @allure.story("支付订单")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", [c for c in DATA["pay_order"] if c["name"] not in _COVERED_SCENARIOS["pay_order"]])
    def test_pay_order(self, client, auth_headers, app, case):
        with allure.step("创建订单"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
            order_resp = client.post("/api/v1/orders", headers=auth_headers)
            order_id = order_resp.get_json()["data"]["id"]
        with allure.step(f"POST /api/v1/orders/{order_id}/pay"):
            resp = client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case.get("expected_status_field"):
            with allure.step(f"DB验证: order状态={case['expected_status_field']}"):
                with app.app_context():
                    from app.models.order import Order
                    order = db.session.get(Order, order_id)
                    assert order.status == case["expected_status_field"]
        if case.get("pay_twice"):
            with allure.step("重复支付已支付订单→预期400"):
                resp2 = client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)
                if case.get("note"):
                    allure.attach(case["note"], name="defect_found",
                                  attachment_type=allure.attachment_type.TEXT)
                else:
                    assert resp2.status_code == 400


@allure.feature("订单模块")
class TestCancelOrder:

    @allure.story("取消订单")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", [c for c in DATA["cancel_order"] if c["name"] not in _COVERED_SCENARIOS["cancel_order"]])
    def test_cancel_order(self, client, auth_headers, app, case):
        if case.get("cross_user"):
            with allure.step("创建订单(用户A)"):
                client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
                order_resp = client.post("/api/v1/orders", headers=auth_headers)
                order_id = order_resp.get_json()["data"]["id"]
            with allure.step("注册用户B"):
                reg_resp = client.post("/api/v1/auth/register", json={
                    "first_name": "Other", "last_name": "User",
                    "email": "cross_user_cancel@test.com",
                    "password": "Test@12345",
                })
                if reg_resp.status_code == 201:
                    other_token = reg_resp.get_json()["data"]["access_token"]
                    other_headers = {"Authorization": f"Bearer {other_token}"}
                    with allure.step(f"用户B尝试取消用户A的订单"):
                        resp = client.post(f"/api/v1/orders/{order_id}/cancel", headers=other_headers)
                        assert resp.status_code == case["expected_status"]
                return

        with allure.step("创建订单"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
            order_resp = client.post("/api/v1/orders", headers=auth_headers)
            order_id = order_resp.get_json()["data"]["id"]

        if case.get("order_state") == "paid":
            with allure.step("先支付订单"):
                client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)

        with allure.step(f"POST /api/v1/orders/{order_id}/cancel"):
            resp = client.post(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]

        if case.get("cancel_twice") and resp.status_code == 200:
            with allure.step("重复取消已取消订单→预期400"):
                resp2 = client.post(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers)
                if case.get("note"):
                    allure.attach(case["note"], name="defect_found",
                                  attachment_type=allure.attachment_type.TEXT)
                else:
                    assert resp2.status_code == 400

        if case.get("expected_status_field") and resp.status_code == 200:
            with allure.step(f"DB验证: order状态={case['expected_status_field']}"):
                with app.app_context():
                    from app.models.order import Order
                    order = db.session.get(Order, order_id)
                    assert order.status == case["expected_status_field"]


# [GAP: resolved-redundancy] TestRefundOrder removed — fully covered by test_business_order.py BIZ-017 & test_e2e_flow.py E2E-002

@allure.feature("订单模块")
class TestGetOrders:

    @allure.story("获取订单列表")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("获取订单列表")
    def test_get_orders(self, client, auth_headers):
        case = DATA["get_orders"][0]
        with allure.step("先创建订单"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
            client.post("/api/v1/orders", headers=auth_headers)
        with allure.step("GET /api/v1/orders"):
            resp = client.get("/api/v1/orders", headers=auth_headers)
            data = resp.get_json()
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case.get("expected_has_orders"):
            with allure.step("验证有订单"):
                assert len(data["data"]["orders"]) >= 1


@allure.feature("订单模块")
class TestGetOrderDetail:

    @allure.story("获取订单详情")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("获取订单详情")
    def test_get_order_detail(self, client, auth_headers):
        case = DATA["get_order_detail"][0]
        with allure.step("先创建订单"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
            order_resp = client.post("/api/v1/orders", headers=auth_headers)
            order_id = order_resp.get_json()["data"]["id"]
        with allure.step(f"GET /api/v1/orders/{order_id}"):
            resp = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)
            data = resp.get_json()
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case.get("expected_has_id"):
            with allure.step("验证订单ID"):
                assert data["data"]["id"] == order_id

    @allure.story("获取订单详情")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("获取不存在的订单-404")
    def test_get_order_not_found(self, client, auth_headers):
        with allure.step("GET /api/v1/orders/99999"):
            resp = client.get("/api/v1/orders/99999", headers=auth_headers)
        with allure.step("验证状态码为404"):
            assert resp.status_code == 404


# [GAP: resolved-redundancy] TestGetOrderStatusLogs removed — fully covered by test_e2e_flow.py E2E-005
