import allure
import pytest
from app.models.product import Product
from app.extensions import db as _db

pytestmark = pytest.mark.unit


@allure.feature("单元测试")
@allure.story("Product模型")
class TestProductModel:

    @allure.title("Product.to_dict 包含所有必要字段")
    def test_to_dict_has_all_fields(self, app, sample_product):
        with app.app_context():
            product = _db.session.get(Product, sample_product.id)
            d = product.to_dict()
            required = ["id", "name", "description", "image", "price",
                        "stock", "type", "category_name", "is_active", "created_at"]
            for field in required:
                assert field in d, f"Missing field: {field}"

    @allure.title("Product 默认is_active为True")
    def test_default_is_active(self, app, sample_product):
        with app.app_context():
            product = _db.session.get(Product, sample_product.id)
            assert product.is_active is True

    @allure.title("Product 默认stock为100")
    def test_default_stock(self, app):
        with app.app_context():
            product = Product(
                name="Default Stock", description="test",
                image="/img/test.webp", price=1000, type="sock",
            )
            _db.session.add(product)
            _db.session.commit()
            assert product.stock == 100

    @allure.title("Product to_dict价格类型为int")
    def test_price_is_int(self, app, sample_product):
        with app.app_context():
            product = _db.session.get(Product, sample_product.id)
            d = product.to_dict()
            assert isinstance(d["price"], int)

    @allure.title("Product 创建负价格商品 - 数据库层面允许(需API层校验)")
    def test_negative_price_at_db_level(self, app):
        with app.app_context():
            product = Product(
                name="Negative Price", description="test",
                image="/img/test.webp", price=-100, stock=10, type="sock",
            )
            _db.session.add(product)
            _db.session.commit()
            assert product.price == -100
