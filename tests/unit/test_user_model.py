import allure
import pytest
from app.models.user import User
from app.extensions import db as _db

pytestmark = pytest.mark.unit


@allure.feature("单元测试")
@allure.story("User模型")
class TestUserModel:

    @allure.title("User.set_password 应生成bcrypt哈希")
    def test_set_password_generates_hash(self, app, sample_user):
        with app.app_context():
            user = _db.session.get(User, sample_user.id)
            assert user.password != "Test@123456"
            assert user.password.startswith("$2")

    @allure.title("User.check_password 正确密码返回True")
    def test_check_password_correct(self, app, sample_user):
        with app.app_context():
            user = _db.session.get(User, sample_user.id)
            assert user.check_password("Test@123456") is True

    @allure.title("User.check_password 错误密码返回False")
    def test_check_password_wrong(self, app, sample_user):
        with app.app_context():
            user = _db.session.get(User, sample_user.id)
            assert user.check_password("WrongPassword") is False

    @allure.title("User.to_dict 包含所有必要字段")
    def test_to_dict_has_all_fields(self, app, sample_user):
        with app.app_context():
            user = _db.session.get(User, sample_user.id)
            d = user.to_dict()
            required = ["id", "first_name", "last_name", "phone", "address",
                        "email", "icon", "balance", "role", "created_at"]
            for field in required:
                assert field in d, f"Missing field: {field}"

    @allure.title("User.to_dict 不包含密码字段")
    def test_to_dict_excludes_password(self, app, sample_user):
        with app.app_context():
            user = _db.session.get(User, sample_user.id)
            d = user.to_dict()
            assert "password" not in d

    @allure.title("User 默认balance为0")
    def test_default_balance_is_zero(self, app):
        with app.app_context():
            user = User(
                first_name="No", last_name="Balance",
                email="nobalance@test.com",
            )
            user.set_password("Test@123456")
            _db.session.add(user)
            _db.session.commit()
            assert user.balance == 0

    @allure.title("User 默认role为customer")
    def test_default_role_is_customer(self, app, sample_user):
        with app.app_context():
            user = _db.session.get(User, sample_user.id)
            assert user.role == "customer"

    @allure.title("User email唯一约束 - 重复邮箱应抛异常")
    def test_email_unique_constraint(self, app, sample_user):
        with app.app_context():
            dup = User(
                first_name="Dup", last_name="User",
                email="unit@test.com",
            )
            dup.set_password("Test@123456")
            _db.session.add(dup)
            with pytest.raises(Exception):
                _db.session.commit()
            _db.session.rollback()
