import allure
import pytest
from app.extensions import db


@allure.feature("E2E业务逻辑")
class TestFullPurchaseFlow:

    @allure.story("完整购买流程")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("E2E-001 注册→登录→加购→下单→支付（集成烟雾测试）")
    def test_register_login_purchase_flow(self, client, app):
        # [GAP: resolved-redundancy] Intermediate DB verifications removed.
        # Module tests (test_auth_yaml, test_cart_yaml, test_order_yaml, test_business_order)
        # already cover individual step assertions. E2E keeps API-level flow as smoke test.
        with allure.step("1. 注册新用户"):
            from tests.utils.faker_data import resolve_faker
            fake_email = resolve_faker("${random_email}")
            resp = client.post("/api/v1/auth/register", json={
                "first_name": "E2E",
                "last_name": "Test",
                "email": fake_email,
                "password": "Test@123456",
                "address": "E2E Test Address",
            })
            assert resp.status_code == 201
            token = resp.get_json()["data"]["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

        with allure.step("1b. 充值余额"):
            client.post("/api/v1/auth/me/recharge", headers=headers, json={"amount": 100000})

        with allure.step("2. 添加商品到购物车"):
            resp = client.post("/api/v1/cart", headers=headers, json={
                "product_id": 1, "quantity": 2,
            })
            assert resp.status_code == 200

        with allure.step("3. 创建订单"):
            resp = client.post("/api/v1/orders", headers=headers)
            assert resp.status_code == 201
            order_id = resp.get_json()["data"]["id"]

        with allure.step("4. 支付订单"):
            resp = client.post(f"/api/v1/orders/{order_id}/pay", headers=headers)
            assert resp.status_code == 200


@allure.feature("E2E业务逻辑")
class TestRefundFlow:

    @allure.story("退款流程")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("E2E-002 下单→支付→退款（集成烟雾测试）")
    def test_refund_flow(self, client, auth_headers, admin_headers, app):
        # [GAP: resolved-redundancy] Intermediate DB verifications removed.
        # Module tests (test_order_yaml, test_admin_yaml, test_business_order)
        # cover individual DB assertions. E2E keeps API-level flow as smoke test.
        with allure.step("1. 加购+下单"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
            order_resp = client.post("/api/v1/orders", headers=auth_headers)
            order_id = order_resp.get_json()["data"]["id"]

        with allure.step("2. 支付"):
            pay_resp = client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)
            assert pay_resp.status_code == 200

        with allure.step("3. 管理员退款"):
            refund_resp = client.post(f"/api/v1/admin/orders/{order_id}/refund", headers=admin_headers)
            assert refund_resp.status_code == 200

        with allure.step("4. DB最终验证: 退款后订单状态为refunded"):
            with app.app_context():
                from app.models.order import Order
                order = db.session.get(Order, order_id)
                assert order.status == "refunded"


@allure.feature("E2E业务逻辑")
class TestAdminShipDeliverFlow:

    @allure.story("发货送达流程")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("E2E-003 下单→支付→发货→送达（集成烟雾测试）")
    def test_ship_deliver_flow(self, client, auth_headers, admin_headers, app):
        # [GAP: resolved-redundancy] Intermediate DB verifications removed.
        # Module tests (test_admin_yaml::TestShipOrder, TestDeliverOrder) cover individual
        # state transitions. E2E keeps API-level flow as smoke test.
        with allure.step("1. 加购+下单+支付"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
            order_resp = client.post("/api/v1/orders", headers=auth_headers)
            order_id = order_resp.get_json()["data"]["id"]
            client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)

        with allure.step("2. 发货"):
            ship_resp = client.put(f"/api/v1/admin/orders/{order_id}/ship", headers=admin_headers)
            assert ship_resp.status_code == 200

        with allure.step("3. 确认送达"):
            deliver_resp = client.put(f"/api/v1/admin/orders/{order_id}/deliver", headers=admin_headers)
            assert deliver_resp.status_code == 200

        with allure.step("4. DB最终验证: 订单状态为delivered"):
            with app.app_context():
                from app.models.order import Order
                assert db.session.get(Order, order_id).status == "delivered"


@allure.feature("E2E业务逻辑")
class TestRechargeAndPurchase:

    @allure.story("充值购买流程")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("E2E-004 充值→加购→下单→支付（集成烟雾测试）")
    def test_recharge_and_purchase(self, client, auth_headers, app):
        # [GAP: resolved-redundancy] Intermediate DB verifications removed.
        # Module tests (test_auth_yaml::TestRecharge, test_business_order::TestPayDeductsBalance)
        # cover balance assertions. E2E keeps API-level flow as smoke test.
        recharge_amount = 10000

        with allure.step(f"1. 充值{recharge_amount}"):
            resp = client.post("/api/v1/auth/me/recharge", headers=auth_headers, json={
                "amount": recharge_amount,
            })
            assert resp.status_code == 200

        with allure.step("2. 加购+下单+支付"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
            order_resp = client.post("/api/v1/orders", headers=auth_headers)
            order_id = order_resp.get_json()["data"]["id"]
            pay_resp = client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)
            assert pay_resp.status_code == 200


@allure.feature("E2E业务逻辑")
class TestOrderStatusLogs:

    @allure.story("订单状态日志")
    @allure.severity(allure.severity_level.MINOR)
    @allure.title("E2E-005 订单全生命周期状态日志（集成烟雾测试）")
    def test_order_status_logs_lifecycle(self, client, auth_headers, admin_headers, app):
        # [GAP: resolved-redundancy] Intermediate DB verifications removed.
        # Module tests (test_order_yaml::TestGetOrderStatusLogs) cover status log assertions.
        # E2E keeps API-level flow as smoke test.
        with allure.step("1. 加购+下单"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
            order_resp = client.post("/api/v1/orders", headers=auth_headers)
            order_id = order_resp.get_json()["data"]["id"]

        with allure.step("2. 支付"):
            client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)

        with allure.step("3. 发货"):
            client.put(f"/api/v1/admin/orders/{order_id}/ship", headers=admin_headers)

        with allure.step("4. 最终DB验证: shipped日志存在"):
            with app.app_context():
                from app.models.order import OrderStatusLog
                logs = OrderStatusLog.query.filter_by(order_id=order_id).all()
                statuses = [l.to_status for l in logs]
                assert "shipped" in statuses
