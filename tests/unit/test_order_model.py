import allure
import pytest
from app.models.order import Order, OrderItem, OrderStatusLog, CartItem
from app.models.user import User
from app.models.product import Product
from app.extensions import db as _db

pytestmark = pytest.mark.unit


@allure.feature("单元测试")
@allure.story("Order模型")
class TestOrderModel:

    @allure.title("Order 默认状态为pending")
    def test_default_status_is_pending(self, app, sample_order):
        with app.app_context():
            order = _db.session.get(Order, sample_order.id)
            assert order.status == Order.STATUS_PENDING

    @allure.title("Order.to_dict 包含所有必要字段")
    def test_to_dict_has_all_fields(self, app, sample_order):
        with app.app_context():
            order = _db.session.get(Order, sample_order.id)
            d = order.to_dict()
            required = ["id", "user_id", "total_amount", "freight",
                        "shipping_address", "shipping_phone", "tracking_number",
                        "status", "items", "status_logs", "created_at", "updated_at"]
            for field in required:
                assert field in d, f"Missing field: {field}"

    @allure.title("Order 状态转换: pending→paid 合法")
    def test_can_transition_pending_to_paid(self, app, sample_order):
        with app.app_context():
            order = _db.session.get(Order, sample_order.id)
            assert order.can_transition_to(Order.STATUS_PAID) is True

    @allure.title("Order 状态转换: pending→cancelled 合法")
    def test_can_transition_pending_to_cancelled(self, app, sample_order):
        with app.app_context():
            order = _db.session.get(Order, sample_order.id)
            assert order.can_transition_to(Order.STATUS_CANCELLED) is True

    @allure.title("Order 状态转换: pending→shipped 非法")
    def test_cannot_transition_pending_to_shipped(self, app, sample_order):
        with app.app_context():
            order = _db.session.get(Order, sample_order.id)
            assert order.can_transition_to(Order.STATUS_SHIPPED) is False

    @allure.title("Order 状态转换: paid→shipped 合法")
    def test_can_transition_paid_to_shipped(self, app, sample_order):
        with app.app_context():
            order = _db.session.get(Order, sample_order.id)
            order.status = Order.STATUS_PAID
            assert order.can_transition_to(Order.STATUS_SHIPPED) is True

    @allure.title("Order 状态转换: paid→refunded 合法")
    def test_can_transition_paid_to_refunded(self, app, sample_order):
        with app.app_context():
            order = _db.session.get(Order, sample_order.id)
            order.status = Order.STATUS_PAID
            assert order.can_transition_to(Order.STATUS_REFUNDED) is True

    @allure.title("Order 状态转换: paid→cancelled 合法(自动退款)")
    def test_can_transition_paid_to_cancelled(self, app, sample_order):
        with app.app_context():
            order = _db.session.get(Order, sample_order.id)
            order.status = Order.STATUS_PAID
            assert order.can_transition_to(Order.STATUS_CANCELLED) is True

    @allure.title("Order 状态转换: shipped→delivered 合法")
    def test_can_transition_shipped_to_delivered(self, app, sample_order):
        with app.app_context():
            order = _db.session.get(Order, sample_order.id)
            order.status = Order.STATUS_SHIPPED
            assert order.can_transition_to(Order.STATUS_DELIVERED) is True

    @allure.title("Order 状态转换: delivered→任何状态 非法")
    def test_cannot_transition_from_delivered(self, app, sample_order):
        with app.app_context():
            order = _db.session.get(Order, sample_order.id)
            order.status = Order.STATUS_DELIVERED
            for target in [Order.STATUS_PENDING, Order.STATUS_PAID,
                           Order.STATUS_SHIPPED, Order.STATUS_CANCELLED,
                           Order.STATUS_REFUNDED]:
                assert order.can_transition_to(target) is False

    @allure.title("Order 状态转换: cancelled→任何状态 非法")
    def test_cannot_transition_from_cancelled(self, app, sample_order):
        with app.app_context():
            order = _db.session.get(Order, sample_order.id)
            order.status = Order.STATUS_CANCELLED
            for target in [Order.STATUS_PENDING, Order.STATUS_PAID,
                           Order.STATUS_SHIPPED, Order.STATUS_DELIVERED,
                           Order.STATUS_REFUNDED]:
                assert order.can_transition_to(target) is False

    @allure.title("Order 状态转换: refunded→任何状态 非法")
    def test_cannot_transition_from_refunded(self, app, sample_order):
        with app.app_context():
            order = _db.session.get(Order, sample_order.id)
            order.status = Order.STATUS_REFUNDED
            for target in [Order.STATUS_PENDING, Order.STATUS_PAID,
                           Order.STATUS_SHIPPED, Order.STATUS_DELIVERED,
                           Order.STATUS_CANCELLED]:
                assert order.can_transition_to(target) is False


@allure.feature("单元测试")
@allure.story("OrderStatusLog模型")
class TestOrderStatusLogModel:

    @allure.title("OrderStatusLog.create 正确创建日志")
    def test_create_log(self, app, sample_order):
        with app.app_context():
            log = OrderStatusLog.create(
                sample_order.id, Order.STATUS_PENDING, Order.STATUS_PAID
            )
            _db.session.commit()
            assert log.order_id == sample_order.id
            assert log.from_status == Order.STATUS_PENDING
            assert log.to_status == Order.STATUS_PAID

    @allure.title("OrderStatusLog.to_dict 包含必要字段")
    def test_to_dict(self, app, sample_order):
        with app.app_context():
            log = OrderStatusLog.create(
                sample_order.id, None, Order.STATUS_PENDING
            )
            _db.session.commit()
            d = log.to_dict()
            assert "id" in d
            assert "order_id" in d
            assert "from_status" in d
            assert "to_status" in d
            assert "created_at" in d


@allure.feature("单元测试")
@allure.story("CartItem模型")
class TestCartItemModel:

    @allure.title("CartItem 默认数量为1")
    def test_default_quantity(self, app, sample_user, sample_product):
        with app.app_context():
            cart = CartItem(
                user_id=sample_user.id,
                product_id=sample_product.id,
            )
            _db.session.add(cart)
            _db.session.commit()
            assert cart.quantity == 1

    @allure.title("CartItem.to_dict 包含商品信息")
    def test_to_dict_has_product_info(self, app, sample_user, sample_product):
        with app.app_context():
            cart = CartItem(
                user_id=sample_user.id,
                product_id=sample_product.id,
                quantity=3,
            )
            _db.session.add(cart)
            _db.session.commit()
            d = cart.to_dict()
            assert d["name"] == "UnitTest Product"
            assert d["price"] == 1999
            assert d["quantity"] == 3
