import pytest
from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.product import Product
from app.models.order import Order, OrderItem, OrderStatusLog, CartItem
from app.models.analytics import (
    UserBehavior, RFMAnalysis, SalesPrediction,
    AssociationRule, ChurnPrediction, ModelMetric, Review,
)


@pytest.fixture(scope="function")
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def sample_user(app):
    with app.app_context():
        user = User(
            first_name="Unit", last_name="Test",
            email="unit@test.com", balance=10000,
        )
        user.set_password("Test@123456")
        _db.session.add(user)
        _db.session.commit()
        yield user


@pytest.fixture(scope="function")
def sample_product(app):
    with app.app_context():
        product = Product(
            name="UnitTest Product", description="for unit test",
            image="/img/test.webp", price=1999, stock=50,
            type="tshirt", category_name="T恤",
        )
        _db.session.add(product)
        _db.session.commit()
        yield product


@pytest.fixture(scope="function")
def sample_order(app, sample_user, sample_product):
    with app.app_context():
        order = Order(
            user_id=sample_user.id,
            total_amount=sample_product.price * 2,
            status=Order.STATUS_PENDING,
        )
        _db.session.add(order)
        _db.session.flush()
        item = OrderItem(
            order_id=order.id,
            product_id=sample_product.id,
            quantity=2,
            unit_price=sample_product.price,
        )
        _db.session.add(item)
        _db.session.commit()
        yield order
