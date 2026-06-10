import allure
import pytest
from app.extensions import db
from tests.utils.yaml_loader import load_yaml

DATA = load_yaml("admin")


@allure.feature("管理员模块")
class TestGetAllOrders:

    @allure.story("获取所有订单")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["get_all_orders"])
    def test_get_all_orders(self, client, auth_headers, admin_headers, case):
        headers = admin_headers if case["as_admin"] else auth_headers
        params = {}
        if case.get("status_filter"):
            params["status"] = case["status_filter"]
        with allure.step(f"GET /api/v1/admin/orders: {case['name']}"):
            resp = client.get("/api/v1/admin/orders", headers=headers, query_string=params)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("管理员模块")
class TestShipOrder:

    @allure.story("发货")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["ship_order"])
    def test_ship_order(self, client, admin_headers, auth_headers, app, case):
        if case.get("ship_pending"):
            with allure.step("创建订单(不支付)"):
                client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
                order_resp = client.post("/api/v1/orders", headers=auth_headers)
                order_id = order_resp.get_json()["data"]["id"]
        else:
            with allure.step("创建并支付订单"):
                client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
                order_resp = client.post("/api/v1/orders", headers=auth_headers)
                order_id = order_resp.get_json()["data"]["id"]
                client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)
        payload = {}
        if case.get("tracking_number"):
            payload["tracking_number"] = case["tracking_number"]
        with allure.step(f"PUT /api/v1/admin/orders/{order_id}/ship"):
            resp = client.put(
                f"/api/v1/admin/orders/{order_id}/ship",
                headers=admin_headers,
                json=payload if payload else None,
            )
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case["expected_status"] == 200:
            with allure.step("DB验证: order状态=shipped"):
                with app.app_context():
                    from app.models.order import Order
                    order = db.session.get(Order, order_id)
                    assert order.status == "shipped"


@allure.feature("管理员模块")
class TestDeliverOrder:

    @allure.story("确认送达")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["deliver_order"])
    def test_deliver_order(self, client, admin_headers, auth_headers, app, case):
        with allure.step("创建→支付"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
            order_resp = client.post("/api/v1/orders", headers=auth_headers)
            order_id = order_resp.get_json()["data"]["id"]
            client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)
        if not case.get("skip_ship"):
            with allure.step("发货"):
                client.put(f"/api/v1/admin/orders/{order_id}/ship", headers=admin_headers)
        with allure.step(f"PUT /api/v1/admin/orders/{order_id}/deliver"):
            resp = client.put(f"/api/v1/admin/orders/{order_id}/deliver", headers=admin_headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case["expected_status"] == 200:
            with allure.step("DB验证: order状态=delivered"):
                with app.app_context():
                    from app.models.order import Order
                    order = db.session.get(Order, order_id)
                    assert order.status == "delivered"


@allure.feature("管理员模块")
class TestRefundOrder:

    @allure.story("退款")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["refund_order"])
    def test_refund_order(self, client, admin_headers, auth_headers, app, case):
        with allure.step("创建→支付"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
            order_resp = client.post("/api/v1/orders", headers=auth_headers)
            order_id = order_resp.get_json()["data"]["id"]
            client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)
        with allure.step(f"POST /api/v1/admin/orders/{order_id}/refund"):
            resp = client.post(f"/api/v1/admin/orders/{order_id}/refund", headers=admin_headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case.get("refund_twice") and resp.status_code == 200:
            with allure.step("重复退款→预期400"):
                resp2 = client.post(f"/api/v1/admin/orders/{order_id}/refund", headers=admin_headers)
                if case.get("note"):
                    allure.attach(case["note"], name="defect_found",
                                  attachment_type=allure.attachment_type.TEXT)
                else:
                    assert resp2.status_code == 400
        if case["expected_status"] == 200:
            with allure.step("DB验证: order状态=refunded"):
                with app.app_context():
                    from app.models.order import Order
                    order = db.session.get(Order, order_id)
                    assert order.status == "refunded"


@allure.feature("管理员模块")
class TestGetAllUsers:

    @allure.story("获取用户列表")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["get_all_users"])
    def test_get_all_users(self, client, auth_headers, admin_headers, case):
        headers = admin_headers if case["as_admin"] else auth_headers
        with allure.step(f"GET /api/v1/admin/users: {case['name']}"):
            resp = client.get("/api/v1/admin/users", headers=headers)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]


@allure.feature("管理员模块")
class TestAdjustBalance:

    @allure.story("调整余额")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["adjust_balance"])
    def test_adjust_balance(self, client, admin_headers, app, case):
        target_user_id = case.get("user_id", 2)
        if target_user_id != 99999:
            with app.app_context():
                from app.models.user import User
                user_before = db.session.get(User, target_user_id)
                balance_before = user_before.balance
        else:
            balance_before = 0

        with allure.step(f"PUT /api/v1/admin/users/{target_user_id}/balance: amount={case['amount']}"):
            resp = client.put(
                f"/api/v1/admin/users/{target_user_id}/balance",
                headers=admin_headers,
                json={"amount": case["amount"]},
            )
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case["expected_status"] == 200:
            with allure.step("DB验证: 余额已调整"):
                with app.app_context():
                    from app.models.user import User
                    user_after = db.session.get(User, target_user_id)
                    assert user_after.balance == balance_before + case["amount"]


@allure.feature("管理员模块")
class TestAdminPayOrder:

    @allure.story("管理员代付")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["admin_pay_order"])
    def test_admin_pay_order(self, client, admin_headers, auth_headers, app, case):
        if case.get("order_id") == 99999:
            target_order_id = 99999
        else:
            with allure.step("准备pending订单"):
                client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
                order_resp = client.post("/api/v1/orders", headers=auth_headers, json={})
                target_order_id = order_resp.get_json()["data"]["id"]

        headers = admin_headers if case["as_admin"] else auth_headers
        with allure.step(f"POST /api/v1/admin/orders/{target_order_id}/pay: {case['name']}"):
            resp = client.post(
                f"/api/v1/admin/orders/{target_order_id}/pay",
                headers=headers, json={},
            )
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case["expected_status"] == 200:
            with allure.step("DB验证: order.status=paid"):
                with app.app_context():
                    from app.models.order import Order
                    order = db.session.get(Order, target_order_id)
                    assert order.status == "paid"


@allure.feature("管理员模块")
class TestAdminReset:

    @allure.story("管理员重置")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["admin_reset"])
    def test_admin_reset(self, client, admin_headers, auth_headers, app, case):
        headers = admin_headers if case["as_admin"] else auth_headers
        payload = {"mode": case.get("mode", "accounts")}
        with allure.step(f"POST /api/v1/admin/reset mode={payload['mode']}"):
            resp = client.post("/api/v1/admin/reset", headers=headers, json=payload)
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
        if case["expected_status"] == 200 and case.get("mode") == "accounts":
            with allure.step("DB验证: admin账户已重置"):
                with app.app_context():
                    from app.models.user import User
                    admin_user = db.session.get(User, 1)
                    assert admin_user.balance == 1000000


@allure.feature("管理员模块")
class TestAdminImportData:

    @allure.story("管理员导入数据")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("{case[name]}")
    @pytest.mark.parametrize("case", DATA["admin_import_data"])
    def test_admin_import_data(self, client, admin_headers, auth_headers, case):
        headers = admin_headers if case["as_admin"] else auth_headers
        with allure.step("POST /api/v1/admin/import-data"):
            resp = client.post("/api/v1/admin/import-data", headers=headers, json={})
        with allure.step("验证状态码"):
            assert resp.status_code == case["expected_status"]
