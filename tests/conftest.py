import os
import pytest
import subprocess
import time
import threading
from datetime import datetime, timezone
from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.product import Product
from app.models.analytics import ModelMetric
from tests.utils.request_util import RequestUtil
from tests.utils.db_util import DBUtil


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:5000")
HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"


# ──────────────────────────────────────────────
# 第一道防线: import 时即检查 FLASK_ENV
# ──────────────────────────────────────────────
def _check_flask_env():
    """强制 FLASK_ENV 必须为 testing。"""
    env = os.environ.get('FLASK_ENV', '')
    if env != 'testing':
        raise RuntimeError(
            f"[DENY] FLASK_ENV='{env}' must be 'testing'! "
            f"Aborting to prevent accidental production database operations."
        )


_check_flask_env()


# ──────────────────────────────────────────────
# 第二道防线: pytest 配置时验证数据库引擎
# ──────────────────────────────────────────────
def pytest_configure(config):
    """pytest 配置钩子: 验证数据库引擎为 SQLite。"""
    app = create_app("testing")
    db_uri = app.config['SQLALCHEMY_DATABASE_URI']
    if 'postgresql' in db_uri.lower() or 'postgres' in db_uri.lower():
        raise RuntimeError(
            f"[DENY] Detected non-SQLite database: {db_uri}. "
            f"Tests must use SQLite, not PostgreSQL."
        )


@pytest.fixture(scope="function")
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        _seed_test_data()
    yield app
    with app.app_context():
        _db.session.remove()
        _db.drop_all()


@pytest.fixture(scope="function")
def client(app):
    with app.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def request_util():
    api = RequestUtil(base_url=BASE_URL)
    yield api
    api.close()


@pytest.fixture(scope="function")
def db_util(app):
    with app.app_context():
        db_uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
    return DBUtil(db_uri)


@pytest.fixture(scope="function")
def auth_headers(client):
    resp = client.post("/api/v1/auth/login", json={
        "email": "customer@shopminer.com", "password": "Customer@123",
    })
    data = resp.get_json()["data"]
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.fixture(scope="function")
def admin_headers(client):
    resp = client.post("/api/v1/auth/login", json={
        "email": "admin@shopminer.com", "password": "Admin@123",
    })
    data = resp.get_json()["data"]
    return {"Authorization": f"Bearer {data['access_token']}"}


@pytest.fixture(scope="function")
def auth_request(request_util):
    request_util.login("customer@shopminer.com", "Customer@123")
    yield request_util
    request_util.clear_token()


@pytest.fixture(scope="function")
def admin_request(request_util):
    request_util.login("admin@shopminer.com", "Admin@123")
    yield request_util
    request_util.clear_token()


_flask_server = None
_flask_thread = None


@pytest.fixture(scope="session")
def live_server():
    global _flask_server, _flask_thread
    if _flask_server is not None:
        yield _flask_server
        return

    _flask_server = subprocess.Popen(
        ["python", "-m", "flask", "run", "--port", "5000"],
        env={**os.environ, "FLASK_APP": "app", "FLASK_ENV": "testing"},
        cwd=os.path.join(os.path.dirname(__file__), ".."),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    time.sleep(2)
    yield _flask_server
    _flask_server.terminate()
    _flask_server.wait()
    _flask_server = None


@pytest.fixture(scope="session")
def browser_type_launch_args():
    return {"headless": HEADLESS}


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    return {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }


@pytest.fixture(scope="function")
def page(browser, context):
    page = context.new_page()
    page.set_default_timeout(10000)
    yield page
    page.close()


@pytest.fixture(autouse=True)
def _attach_screenshot_on_failure(page, request):
    yield
    if hasattr(request.node, "rep_call") and request.node.rep_call.failed:
        screenshot_dir = os.path.join(os.path.dirname(__file__), "report", "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)
        screenshot_path = os.path.join(screenshot_dir, f"{request.node.name}.png")
        try:
            page.screenshot(path=screenshot_path, full_page=True)
        except Exception:
            pass


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    setattr(item, f"rep_{rep.when}", rep)


def _seed_test_data():
    admin = User(
        first_name="Admin", last_name="User", address="Admin Address",
        email="admin@shopminer.com", role="admin", balance=1000000,
    )
    admin.set_password("Admin@123")
    _db.session.add(admin)

    customer = User(
        first_name="Test", last_name="Customer", address="123 Test St",
        email="customer@shopminer.com", balance=500000,
    )
    customer.set_password("Customer@123")
    _db.session.add(customer)

    products = [
        Product(name="Test T-Shirt A", description="A test t-shirt", image="/img/tshirtA.webp", price=2999, stock=100, type="tshirt"),
        Product(name="Test Pants A", description="Test pants", image="/img/pantsA.jpg", price=5999, stock=50, type="pants"),
        Product(name="Test Socks A", description="Test socks", image="/img/sockA.webp", price=999, stock=200, type="sock"),
        Product(name="Test T-Shirt B", description="Another test t-shirt", image="/img/tshirtB.webp", price=3999, stock=0, type="tshirt"),
    ]
    _db.session.add_all(products)

    model_metrics = [
        ModelMetric(model_name="Clustering", metric_name="version", metric_value=0, detail="v4_optuna"),
        ModelMetric(model_name="Clustering", metric_name="K", metric_value=4, detail="4"),
        ModelMetric(model_name="Clustering", metric_name="silhouette_score", metric_value=0.36, detail="0.36"),

        ModelMetric(model_name="Churn", metric_name="version", metric_value=0, detail="v8_xgb_shap_K50"),
        ModelMetric(model_name="Churn", metric_name="test_auc", metric_value=0.77, detail="0.77"),
        ModelMetric(model_name="Churn", metric_name="oot_auc_mean", metric_value=0.91, detail="0.91"),

        ModelMetric(model_name="SalesForecast", metric_name="version", metric_value=0, detail="v3_calendar_features"),
        ModelMetric(model_name="SalesForecast", metric_name="best_smape", metric_value=4.86, detail="4.86%"),
        ModelMetric(model_name="SalesForecast", metric_name="best_mae", metric_value=8109.34, detail="8109.34"),
        ModelMetric(model_name="SalesForecast", metric_name="best_r2", metric_value=0.9466, detail="0.9466"),
        ModelMetric(model_name="SalesForecast", metric_name="cv_smape_mean", metric_value=12.45, detail="12.45% +/- 7.34%"),
        ModelMetric(model_name="SalesForecast", metric_name="cv_smape_std", metric_value=7.34, detail="±7.34%"),
        ModelMetric(model_name="SalesForecast", metric_name="cv_folds", metric_value=5, detail="5 折"),

        ModelMetric(model_name="Association", metric_name="version", metric_value=0, detail="v3_dual_level"),
        ModelMetric(model_name="Association", metric_name="global_rules_count", metric_value=694, detail="694"),
    ]
    _db.session.add_all(model_metrics)
    _db.session.commit()
