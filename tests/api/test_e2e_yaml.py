import allure
import pytest
from app.extensions import db


@allure.feature("E2E业务逻辑")
class TestFullPurchaseFlow:

    @allure.story("完整购买流程")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.title("E2E-001 注册→登录→加购→下单→支付→DB双重验证")
    def test_register_login_purchase_flow(self, client, app):
        with allure.step("1. 注册新用?"):
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

        with allure.step("1b. 充值余?"):
            client.post("/api/v1/auth/me/recharge", headers=headers, json={"amount": 100000})

        with allure.step("2. DB验证: user表新增记?"):
            with app.app_context():
                from app.models.user import User
                user = User.query.filter_by(email=fake_email).first()
                assert user is not None
                user_id = user.id
                balance_before = user.balance

        with allure.step("3. 添加商品到购物车"):
            resp = client.post("/api/v1/cart", headers=headers, json={
                "product_id": 1, "quantity": 2,
            })
            assert resp.status_code == 200

        with allure.step("4. DB验证: cart_item表新增记?"):
            with app.app_context():
                from app.models.order import CartItem
                item = CartItem.query.filter_by(user_id=user_id, product_id=1).first()
                assert item is not None
                assert item.quantity == 2

        with allure.step("5. 创建订单"):
            resp = client.post("/api/v1/orders", headers=headers)
            assert resp.status_code == 201
            order_id = resp.get_json()["data"]["id"]

        with allure.step("6. DB验证: order表新增，cart已清空"):
            with app.app_context():
                from app.models.order import Order, CartItem
                order = db.session.get(Order, order_id)
                assert order is not None
                assert order.status == "pending"
                cart_items = CartItem.query.filter_by(user_id=user_id).all()
                assert len(cart_items) == 0

        with allure.step("7. 支付订单"):
            resp = client.post(f"/api/v1/orders/{order_id}/pay", headers=headers)
            assert resp.status_code == 200

        with allure.step("8. DB验证: order状态: paid+user余额扣减"):
            with app.app_context():
                from app.models.order import Order
                from app.models.user import User
                order = db.session.get(Order, order_id)
                assert order.status == "paid"
                user = db.session.get(User, user_id)
                assert user.balance == balance_before - order.total_amount


@allure.feature("E2E业务逻辑")
class TestRefundFlow:

    @allure.story("退款流?")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("E2E-002 下单→支付→退款→DB验证余额恢复")
    def test_refund_flow(self, client, auth_headers, admin_headers, app):
        with allure.step("1. 记录用户初始余额"):
            with app.app_context():
                from app.models.user import User
                user_before = User.query.filter_by(email="customer@shopminer.com").first()
                balance_before = user_before.balance

        with allure.step("2. 加购+下单"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
            order_resp = client.post("/api/v1/orders", headers=auth_headers)
            order_id = order_resp.get_json()["data"]["id"]

        with allure.step("3. 支付"):
            pay_resp = client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)
            assert pay_resp.status_code == 200

        with allure.step("4. DB验证: 余额已扣?"):
            with app.app_context():
                from app.models.user import User
                from app.models.order import Order
                user_paid = User.query.filter_by(email="customer@shopminer.com").first()
                order = db.session.get(Order, order_id)
                assert user_paid.balance == balance_before - order.total_amount

        with allure.step("5. 管理员退?"):
            refund_resp = client.post(f"/api/v1/admin/orders/{order_id}/refund", headers=admin_headers)
            assert refund_resp.status_code == 200

        with allure.step("6. DB验证: order=refunded+余额恢复"):
            with app.app_context():
                from app.models.order import Order
                from app.models.user import User
                order = db.session.get(Order, order_id)
                assert order.status == "refunded"
                user_refunded = User.query.filter_by(email="customer@shopminer.com").first()
                assert user_refunded.balance == balance_before


@allure.feature("E2E业务逻辑")
class TestAdminShipDeliverFlow:

    @allure.story("发货送达流程")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("E2E-003 下单→支付→发货→送达→DB验证状态流?")
    def test_ship_deliver_flow(self, client, auth_headers, admin_headers, app):
        with allure.step("1. 加购+下单+支付"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
            order_resp = client.post("/api/v1/orders", headers=auth_headers)
            order_id = order_resp.get_json()["data"]["id"]
            client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)

        with allure.step("2. DB验证: order=paid"):
            with app.app_context():
                from app.models.order import Order
                assert db.session.get(Order, order_id).status == "paid"

        with allure.step("3. 发货"):
            ship_resp = client.put(f"/api/v1/admin/orders/{order_id}/ship", headers=admin_headers)
            assert ship_resp.status_code == 200

        with allure.step("4. DB验证: order=shipped"):
            with app.app_context():
                from app.models.order import Order
                assert db.session.get(Order, order_id).status == "shipped"

        with allure.step("5. 确认送达"):
            deliver_resp = client.put(f"/api/v1/admin/orders/{order_id}/deliver", headers=admin_headers)
            assert deliver_resp.status_code == 200

        with allure.step("6. DB验证: order=delivered"):
            with app.app_context():
                from app.models.order import Order
                assert db.session.get(Order, order_id).status == "delivered"


@allure.feature("E2E业务逻辑")
class TestRechargeAndPurchase:

    @allure.story("充值购买流?")
    @allure.severity(allure.severity_level.NORMAL)
    @allure.title("E2E-004 充值→加购→下单→支付→DB验证余额")
    def test_recharge_and_purchase(self, client, auth_headers, app):
        recharge_amount = 10000

        with allure.step("1. 记录初始余额"):
            with app.app_context():
                from app.models.user import User
                user = User.query.filter_by(email="customer@shopminer.com").first()
                balance_before = user.balance

        with allure.step(f"2. 充值{recharge_amount}"):
            resp = client.post("/api/v1/auth/me/recharge", headers=auth_headers, json={
                "amount": recharge_amount,
            })
            assert resp.status_code == 200

        with allure.step("3. DB验证: 余额增加"):
            with app.app_context():
                from app.models.user import User
                user = User.query.filter_by(email="customer@shopminer.com").first()
                assert user.balance == balance_before + recharge_amount

        with allure.step("4. 加购+下单+支付"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
            order_resp = client.post("/api/v1/orders", headers=auth_headers)
            order_id = order_resp.get_json()["data"]["id"]
            client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)

        with allure.step("5. DB验证: 余额=充值后-订单金额"):
            with app.app_context():
                from app.models.order import Order
                from app.models.user import User
                order = db.session.get(Order, order_id)
                user = User.query.filter_by(email="customer@shopminer.com").first()
                assert user.balance == balance_before + recharge_amount - order.total_amount


@allure.feature("E2E业务逻辑")
class TestOrderStatusLogs:

    @allure.story("订单状态日?")
    @allure.severity(allure.severity_level.MINOR)
    @allure.title("E2E-005 订单全生命周期状态日志→DB验证")
    def test_order_status_logs_lifecycle(self, client, auth_headers, admin_headers, app):
        with allure.step("1. 加购+下单"):
            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})
            order_resp = client.post("/api/v1/orders", headers=auth_headers)
            order_id = order_resp.get_json()["data"]["id"]

        with allure.step("2. DB验证: pending日志"):
            with app.app_context():
                from app.models.order import OrderStatusLog
                logs = OrderStatusLog.query.filter_by(order_id=order_id).all()
                assert any(l.to_status == "pending" for l in logs)

        with allure.step("3. 支付"):
            client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)

        with allure.step("4. DB验证: paid日志"):
            with app.app_context():
                from app.models.order import OrderStatusLog
                logs = OrderStatusLog.query.filter_by(order_id=order_id).all()
                statuses = [l.to_status for l in logs]
                assert "pending" in statuses
                assert "paid" in statuses

        with allure.step("5. 发货"):
            client.put(f"/api/v1/admin/orders/{order_id}/ship", headers=admin_headers)

        with allure.step("6. DB验证: shipped日志"):
            with app.app_context():
                from app.models.order import OrderStatusLog
                logs = OrderStatusLog.query.filter_by(order_id=order_id).all()
                statuses = [l.to_status for l in logs]
                assert "shipped" in statuses
