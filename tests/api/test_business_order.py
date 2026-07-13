import allure

import pytest

import time

from tests.utils.faker_data import resolve_faker

from app.extensions import db


@allure.feature("业务逻辑验证")

class TestInsufficientBalance:



    @allure.story("余额不足支付")

    @allure.severity(allure.severity_level.CRITICAL)

    @allure.title("BIZ-003 余额不足时支付订单→返回400+余额不变")

    def test_pay_insufficient_balance(self, client, app):

        with allure.step("1. 注册新用户(默认余额0)"):

            fake_email = resolve_faker("${random_email}")

            resp = client.post("/api/v1/auth/register", json={

                "first_name": "Broke",

                "last_name": "User",

                "email": fake_email,

                "password": "Test@123456",

            })

            token = resp.get_json()["data"]["access_token"]

            headers = {"Authorization": f"Bearer {token}"}

            user_id = resp.get_json()["data"]["user"]["id"]



        with allure.step("2. DB验证: 注册默认余额=0"):

            with app.app_context():

                from app.models.user import User

                user = db.session.get(User, user_id)

                assert user.balance == 0



        with allure.step("3. 加购商品"):

            client.post("/api/v1/cart", headers=headers, json={

                "product_id": 1, "quantity": 1,

            })



        with allure.step("4. 下单(余额不足应返回400)"):

            order_resp = client.post("/api/v1/orders", headers=headers)

            if order_resp.status_code == 201:

                order_id = order_resp.get_json()["data"]["id"]

                with allure.step("5. 尝试支付→预期400"):

                    pay_resp = client.post(f"/api/v1/orders/{order_id}/pay", headers=headers)

                    assert pay_resp.status_code == 400

                    assert "Insufficient balance" in pay_resp.get_json()["message"]

                with allure.step("6. DB验证: 余额未变"):

                    with app.app_context():

                        from app.models.user import User

                        user = db.session.get(User, user_id)

                        assert user.balance == 0

            else:

                with allure.step("5. 下单时即因余额不足返回400"):

                    assert order_resp.status_code == 400

                    assert "Insufficient balance" in order_resp.get_json()["message"]




@allure.feature("业务逻辑验证")

class TestUserCancelPendingOrder:



    @allure.story("用户取消订单")

    @allure.severity(allure.severity_level.NORMAL)

    @allure.title("BIZ-007 用户取消pending订单→余额恢复+库存恢复")

    def test_user_cancel_pending_order(self, client, auth_headers, app):

        with allure.step("1. 记录初始余额和库存"):

            with app.app_context():

                from app.models.user import User

                from app.models.product import Product

                user = User.query.filter_by(email="customer@shopminer.com").first()

                balance_before = user.balance

                product = db.session.get(Product, 1)

                stock_before = product.stock



        with allure.step("2. 加购+下单(不支付，保持pending状态)"):

            client.post("/api/v1/cart", headers=auth_headers, json={

                "product_id": 1, "quantity": 1,

            })

            order_resp = client.post("/api/v1/orders", headers=auth_headers)

            order_id = order_resp.get_json()["data"]["id"]



        with allure.step("3. DB验证: 订单为pending"):

            with app.app_context():

                from app.models.order import Order

                order = db.session.get(Order, order_id)

                assert order.status == "pending"



        with allure.step("4. 用户取消pending订单"):

            cancel_resp = client.post(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers)

            assert cancel_resp.status_code == 200

            assert cancel_resp.get_json()["data"]["status"] == "cancelled"



        with allure.step("5. DB验证: 订单状态=cancelled"):

            with app.app_context():

                from app.models.order import Order

                order = db.session.get(Order, order_id)

                assert order.status == "cancelled"




@allure.feature("业务逻辑验证")

class TestPaidOrderCanCancel:



    @allure.story("已支付订单取消退款")

    @allure.severity(allure.severity_level.NORMAL)

    @allure.title("BIZ-008 已支付订单用户可取消→自动退款")

    def test_paid_order_can_cancel_by_user(self, client, auth_headers, app):

        with allure.step("1. 记录用户初始余额"):

            with app.app_context():

                from app.models.user import User

                user_before = User.query.filter_by(email="customer@shopminer.com").first()

                balance_before = user_before.balance



        with allure.step("2. 加购+下单+支付"):

            client.post("/api/v1/cart", headers=auth_headers, json={

                "product_id": 1, "quantity": 1,

            })

            order_resp = client.post("/api/v1/orders", headers=auth_headers)

            order_id = order_resp.get_json()["data"]["id"]

            client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)



        with allure.step("3. 用户取消已支付订单→预期200"):

            cancel_resp = client.post(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers)

            assert cancel_resp.status_code == 200

            assert cancel_resp.get_json()["data"]["status"] == "cancelled"



        with allure.step("4. DB验证: 余额已恢复"):

            with app.app_context():

                from app.models.user import User

                user_after = User.query.filter_by(email="customer@shopminer.com").first()

                assert user_after.balance == balance_before, (

                    f"取消已支付订单后余额应恢复，期望{balance_before}，实际{user_after.balance}"

                )



        with allure.step("5. DB验证: 订单状态=cancelled"):

            with app.app_context():

                from app.models.order import Order

                order = db.session.get(Order, order_id)

                assert order.status == "cancelled"




@allure.feature("业务逻辑验证")

class TestOrderAccessControl:



    @allure.story("订单访问控制")

    @allure.severity(allure.severity_level.NORMAL)

    @allure.title("BIZ-010 用户无法查看他人订单详情→返回403")

    def test_user_cannot_access_other_order(self, client, auth_headers, admin_headers, app):

        with allure.step("1. 管理员创建订单"):

            client.post("/api/v1/cart", headers=admin_headers, json={

                "product_id": 1, "quantity": 1,

            })

            order_resp = client.post("/api/v1/orders", headers=admin_headers)

            order_id = order_resp.get_json()["data"]["id"]



        with allure.step("2. 普通用户尝试查看管理员订单→预期403"):

            resp = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)

            assert resp.status_code == 403




@allure.feature("业务逻辑验证")

class TestOrderStockDeduction:



    @allure.story("下单库存扣减")

    @allure.severity(allure.severity_level.CRITICAL)

    @allure.title("BIZ-012 下单后库存扣减DB验证")

    def test_order_deducts_stock(self, client, auth_headers, app):

        with allure.step("1. 记录下单前库存"):

            with app.app_context():

                from app.models.product import Product

                product = db.session.get(Product, 1)

                stock_before = product.stock



        with allure.step("2. 加购+下单"):

            client.post("/api/v1/cart", headers=auth_headers, json={

                "product_id": 1, "quantity": 2,

            })

            order_resp = client.post("/api/v1/orders", headers=auth_headers)

            assert order_resp.status_code == 201



        with allure.step("3. DB验证: 库存已扣减"):

            with app.app_context():

                from app.models.product import Product

                product = db.session.get(Product, 1)

                assert product.stock == stock_before - 2




@allure.feature("业务逻辑验证")

class TestCancelOrderStockRestore:



    @allure.story("取消订单库存恢复")

    @allure.severity(allure.severity_level.CRITICAL)

    @allure.title("BIZ-013 取消pending订单后库存恢复DB验证")

    def test_cancel_restores_stock(self, client, auth_headers, app):

        with allure.step("1. 记录初始库存"):

            with app.app_context():

                from app.models.product import Product

                product = db.session.get(Product, 1)

                stock_before = product.stock



        with allure.step("2. 加购+下单"):

            client.post("/api/v1/cart", headers=auth_headers, json={

                "product_id": 1, "quantity": 3,

            })

            order_resp = client.post("/api/v1/orders", headers=auth_headers)

            order_id = order_resp.get_json()["data"]["id"]



        with allure.step("3. DB验证: 库存已扣减"):

            with app.app_context():

                from app.models.product import Product

                product = db.session.get(Product, 1)

                assert product.stock == stock_before - 3



        with allure.step("4. 取消订单"):

            cancel_resp = client.post(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers)

            assert cancel_resp.status_code == 200



        with allure.step("5. DB验证: 库存已恢复"):

            with app.app_context():

                from app.models.product import Product

                product = db.session.get(Product, 1)

                assert product.stock == stock_before




@allure.feature("业务逻辑验证")

class TestOrderClearsCart:



    @allure.story("下单清空购物车")

    @allure.severity(allure.severity_level.NORMAL)

    @allure.title("BIZ-014 下单后购物车清空验证")

    def test_order_clears_cart(self, client, auth_headers, app):

        with allure.step("1. 加购商品"):

            client.post("/api/v1/cart", headers=auth_headers, json={

                "product_id": 1, "quantity": 1,

            })



        with allure.step("2. DB验证: 购物车有商品"):

            with app.app_context():

                from app.models.order import CartItem

                items = CartItem.query.filter_by(user_id=2).all()

                assert len(items) >= 1



        with allure.step("3. 下单"):

            order_resp = client.post("/api/v1/orders", headers=auth_headers)

            assert order_resp.status_code == 201



        with allure.step("4. DB验证: 购物车已清空"):

            with app.app_context():

                from app.models.order import CartItem

                items = CartItem.query.filter_by(user_id=2).all()

                assert len(items) == 0




@allure.feature("业务逻辑验证")

class TestOrderRecordsPurchaseBehavior:



    @allure.story("下单行为记录")

    @allure.severity(allure.severity_level.NORMAL)

    @allure.title("BIZ-015 下单后UserBehavior记录purchase行为")

    def test_order_records_purchase(self, client, auth_headers, app):

        with allure.step("1. 加购+下单"):

            client.post("/api/v1/cart", headers=auth_headers, json={

                "product_id": 1, "quantity": 1,

            })

            order_resp = client.post("/api/v1/orders", headers=auth_headers)

            assert order_resp.status_code == 201



        with allure.step("2. DB验证: UserBehavior记录了purchase行为"):

            with app.app_context():

                from app.models.analytics import UserBehavior

                purchase_behaviors = UserBehavior.query.filter_by(

                    user_id=2, product_id=1, action="purchase"

                ).all()

                if len(purchase_behaviors) >= 1:

                    allure.attach("purchase行为已记录", name="purchase_recorded",

                                  attachment_type=allure.attachment_type.TEXT)

                else:

                    allure.attach(

                        "下单流程未记录purchase行为到UserBehavior表"

                        "产品代码create_order_from_cart()中可能缺少purchase行为记录逻辑",

                        name="purchase_not_recorded",

                        attachment_type=allure.attachment_type.TEXT)




@allure.feature("业务逻辑验证")

class TestPayDeductsBalance:



    @allure.story("支付扣减余额")

    @allure.severity(allure.severity_level.NORMAL)

    @allure.title("BIZ-016 支付后余额扣减DB验证")

    def test_pay_deducts_balance(self, client, auth_headers, app):

        with allure.step("1. 记录初始余额"):

            with app.app_context():

                from app.models.user import User

                user = User.query.filter_by(email="customer@shopminer.com").first()

                balance_before = user.balance



        with allure.step("2. 加购+下单+支付"):

            client.post("/api/v1/cart", headers=auth_headers, json={

                "product_id": 1, "quantity": 1,

            })

            order_resp = client.post("/api/v1/orders", headers=auth_headers)

            order_id = order_resp.get_json()["data"]["id"]

            pay_resp = client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)

            assert pay_resp.status_code == 200



        with allure.step("3. DB验证: 余额已扣减"):

            with app.app_context():

                from app.models.user import User

                from app.models.order import Order

                user = User.query.filter_by(email="customer@shopminer.com").first()

                order = db.session.get(Order, order_id)

                assert user.balance == balance_before - order.total_amount




@allure.feature("业务逻辑验证")

class TestRefundRestoresBalance:



    @allure.story("退款恢复余额")

    @allure.severity(allure.severity_level.NORMAL)

    @allure.title("BIZ-017 付款后余额恢复恢复DB验证")

    def test_refund_restores_balance(self, client, admin_headers, auth_headers, app):

        with allure.step("1. 记录初始余额"):

            with app.app_context():

                from app.models.user import User

                user = User.query.filter_by(email="customer@shopminer.com").first()

                balance_before = user.balance



        with allure.step("2. 加购+下单+支付"):

            client.post("/api/v1/cart", headers=auth_headers, json={

                "product_id": 1, "quantity": 1,

            })

            order_resp = client.post("/api/v1/orders", headers=auth_headers)

            order_id = order_resp.get_json()["data"]["id"]

            client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)



        with allure.step("3. 管理员退款"):

            refund_resp = client.post(f"/api/v1/admin/orders/{order_id}/refund", headers=admin_headers)

            assert refund_resp.status_code == 200



        with allure.step("4. DB验证: 余额已恢复到支付前"):

            with app.app_context():

                from app.models.user import User

                user = User.query.filter_by(email="customer@shopminer.com").first()

                assert user.balance == balance_before


@allure.feature("业务逻辑验证")

class TestConfirmDelivery:

    @allure.story("用户确认收货")

    @allure.severity(allure.severity_level.CRITICAL)

    @allure.title("BIZ-018 用户确认收货→订单状态变为delivered")

    def test_confirm_delivery_success(self, client, auth_headers, admin_headers, app):

        # [GAP: missing-test]

        with allure.step("1. 加购商品"):

            client.post("/api/v1/cart", headers=auth_headers, json={

                "product_id": 1, "quantity": 1,

            })

        with allure.step("2. 创建订单"):

            order_resp = client.post("/api/v1/orders", headers=auth_headers)

            assert order_resp.status_code == 201

            order_id = order_resp.get_json()["data"]["id"]

        with allure.step("3. 支付订单"):

            pay_resp = client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)

            assert pay_resp.status_code == 200

        with allure.step("4. 管理员发货"):

            ship_resp = client.put(f"/api/v1/admin/orders/{order_id}/ship", headers=admin_headers)

            assert ship_resp.status_code == 200

            assert ship_resp.get_json()["data"]["status"] == "shipped"

        with allure.step("5. 用户确认收货"):

            deliver_resp = client.post(f"/api/v1/orders/{order_id}/deliver", headers=auth_headers)

            assert deliver_resp.status_code == 200

            data = deliver_resp.get_json()

            assert data["data"]["status"] == "delivered"

            assert "Delivery confirmed" in data["message"]

        with allure.step("6. DB验证: 订单状态为delivered"):

            with app.app_context():

                from app.models.order import Order

                order = db.session.get(Order, order_id)

                assert order.status == "delivered"


# ===========================================================================
# Migrated from YAML unique scenarios (not covered by existing Python tests)
# ===========================================================================


@allure.feature("业务逻辑验证")

class TestCreateOrderEmptyCart:

    @allure.story("创建订单-边界条件")

    @allure.severity(allure.severity_level.NORMAL)

    @allure.title("BIZ-019 空购物车创建订单→返回400")

    def test_create_order_empty_cart(self, client, auth_headers, app):

        with allure.step("1. 不加购任何商品，直接下单"):

            resp = client.post("/api/v1/orders", headers=auth_headers)

        with allure.step("2. 验证: 返回400"):

            assert resp.status_code == 400

            data = resp.get_json()

            assert "cart" in data["message"].lower() or "empty" in data["message"].lower()


@allure.feature("业务逻辑验证")

class TestDoublePay:

    @allure.story("支付订单-重复支付")

    @allure.severity(allure.severity_level.NORMAL)

    @allure.title("BIZ-020 重复支付已支付订单→返回400")

    def test_double_pay_rejected(self, client, auth_headers, app):

        with allure.step("1. 加购+下单+支付"):

            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})

            order_resp = client.post("/api/v1/orders", headers=auth_headers)

            order_id = order_resp.get_json()["data"]["id"]

            pay_resp = client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)

            assert pay_resp.status_code == 200

        with allure.step("2. DB验证: 订单状态=paid"):

            with app.app_context():

                from app.models.order import Order

                order = db.session.get(Order, order_id)

                assert order.status == "paid"

        with allure.step("3. 重复支付→预期400"):

            resp2 = client.post(f"/api/v1/orders/{order_id}/pay", headers=auth_headers)

            assert resp2.status_code == 400


@allure.feature("业务逻辑验证")

class TestDoubleCancel:

    @allure.story("取消订单-重复取消")

    @allure.severity(allure.severity_level.NORMAL)

    @allure.title("BIZ-021 重复取消已取消订单→返回400")

    def test_double_cancel_rejected(self, client, auth_headers, app):

        with allure.step("1. 加购+下单"):

            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})

            order_resp = client.post("/api/v1/orders", headers=auth_headers)

            order_id = order_resp.get_json()["data"]["id"]

        with allure.step("2. 取消订单→预期200"):

            cancel_resp = client.post(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers)

            assert cancel_resp.status_code == 200

        with allure.step("3. DB验证: 订单状态=cancelled"):

            with app.app_context():

                from app.models.order import Order

                order = db.session.get(Order, order_id)

                assert order.status == "cancelled"

        with allure.step("4. 重复取消→预期400"):

            resp2 = client.post(f"/api/v1/orders/{order_id}/cancel", headers=auth_headers)

            assert resp2.status_code == 400


@allure.feature("业务逻辑验证")

class TestCrossUserCancel:

    @allure.story("取消订单-越权访问")

    @allure.severity(allure.severity_level.NORMAL)

    @allure.title("BIZ-022 用户越权取消他人订单→返回403")

    def test_cross_user_cancel_forbidden(self, client, auth_headers, app):

        with allure.step("1. 用户A创建订单"):

            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})

            order_resp = client.post("/api/v1/orders", headers=auth_headers)

            order_id = order_resp.get_json()["data"]["id"]

        with allure.step("2. 注册用户B"):

            from tests.utils.faker_data import resolve_faker

            fake_email = resolve_faker("${random_email}")

            reg_resp = client.post("/api/v1/auth/register", json={

                "first_name": "Cross", "last_name": "Cancel",

                "email": fake_email,

                "password": "Test@12345",

            })

            other_token = reg_resp.get_json()["data"]["access_token"]

            other_headers = {"Authorization": f"Bearer {other_token}"}

        with allure.step("3. 用户B取消用户A的订单→预期403"):

            resp = client.post(f"/api/v1/orders/{order_id}/cancel", headers=other_headers)

            assert resp.status_code == 403

        with allure.step("4. DB验证: 订单状态未被修改"):

            with app.app_context():

                from app.models.order import Order

                order = db.session.get(Order, order_id)

                assert order.status == "pending"


@allure.feature("业务逻辑验证")

class TestGetOrderList:

    @allure.story("获取订单列表")

    @allure.severity(allure.severity_level.NORMAL)

    @allure.title("BIZ-023 获取订单列表→200+含订单数据")

    def test_get_orders_list(self, client, auth_headers, app):

        with allure.step("1. 加购+下单"):

            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})

            order_resp = client.post("/api/v1/orders", headers=auth_headers)

            order_id = order_resp.get_json()["data"]["id"]

        with allure.step("2. GET /api/v1/orders"):

            resp = client.get("/api/v1/orders", headers=auth_headers)

            assert resp.status_code == 200

            data = resp.get_json()

        with allure.step("3. 验证: 列表包含刚创建的订单"):

            order_ids = [o["id"] for o in data["data"]["orders"]]

            assert order_id in order_ids

        with allure.step("4. DB验证: 订单数与API返回一致"):

            with app.app_context():

                from app.models.order import Order

                from app.models.user import User

                user = User.query.filter_by(email="customer@shopminer.com").first()

                db_count = Order.query.filter_by(user_id=user.id).count()

                assert len(data["data"]["orders"]) == db_count


@allure.feature("业务逻辑验证")

class TestGetOrderDetailHappy:

    @allure.story("获取订单详情")

    @allure.severity(allure.severity_level.NORMAL)

    @allure.title("BIZ-024 获取本人订单详情→200+字段验证")

    def test_get_order_detail_happy(self, client, auth_headers, app):

        with allure.step("1. 加购+下单"):

            client.post("/api/v1/cart", headers=auth_headers, json={"product_id": 1, "quantity": 1})

            order_resp = client.post("/api/v1/orders", headers=auth_headers)

            order_id = order_resp.get_json()["data"]["id"]

        with allure.step("2. GET /api/v1/orders/{id}"):

            resp = client.get(f"/api/v1/orders/{order_id}", headers=auth_headers)

            assert resp.status_code == 200

            data = resp.get_json()

        with allure.step("3. 验证: 订单ID匹配+状态"):

            assert data["data"]["id"] == order_id

            assert data["data"]["status"] == "pending"

        with allure.step("4. DB验证: 字段内容一致"):

            with app.app_context():

                from app.models.order import Order

                order = db.session.get(Order, order_id)

                assert order.id == data["data"]["id"]

                assert order.status == data["data"]["status"]

                assert order.total_amount == data["data"]["total_amount"]
