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
    """Create a Flask app with in-memory SQLite database for service testing."""
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def db(app):
    """Provide the database session bound to the app context."""
    with app.app_context():
        yield _db


@pytest.fixture(scope="function")
def sample_user(app):
    """Create a sample user with known credentials for service testing."""
    with app.app_context():
        user = User(
            first_name="Service", last_name="Tester",
            email="svc_test@shopminer.com",
            address="456 Service Ave",
            icon="icon_bear.png",
            balance=50000,
        )
        user.set_password("TestPass123")
        _db.session.add(user)
        _db.session.commit()
        yield user


@pytest.fixture(scope="function")
def sample_product(app):
    """Create a sample active product for service testing."""
    with app.app_context():
        product = Product(
            name="Service Test Product",
            description="Created by service test fixture",
            image="/img/svc_test.webp",
            price=2999,
            stock=100,
            type="tshirt",
            category_name="T恤",
            is_active=True,
        )
        _db.session.add(product)
        _db.session.commit()
        yield product


@pytest.fixture(scope="function")
def sample_order(app, sample_user, sample_product):
    """Create a sample order with order items for service testing.

    Depends on sample_user and sample_product fixtures.
    """
    with app.app_context():
        order = Order(
            user_id=sample_user.id,
            total_amount=sample_product.price * 2,
            shipping_address="456 Service Ave",
            shipping_phone="13800138000",
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
        _db.session.flush()

        OrderStatusLog.create(order.id, None, Order.STATUS_PENDING)
        _db.session.commit()
        yield order


@pytest.fixture(scope="function")
def auth_service(app):
    """Return the auth_service module for testing."""
    from app.services import auth_service
    return auth_service


@pytest.fixture(scope="function")
def order_service(app):
    """Return the order_service module for testing."""
    from app.services import order_service
    return order_service


@pytest.fixture(scope="function")
def analytics_service(app):
    """Return the analytics_service module for testing."""
    from app.services import analytics_service
    return analytics_service
