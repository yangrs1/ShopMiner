"""独立Flask服务?"- 供Playwright测试使用"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app import create_app
from app.extensions import db as _db

db_path = os.environ.get("WEB_TEST_DB", "")
app = create_app("testing")
app.config["TESTING"] = False
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{db_path}"
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {"connect_args": {"check_same_thread": False}}

try:
    app.extensions["limiter"].enabled = False
except Exception:
    pass

with app.app_context():
    _db.create_all()

    from app.models.user import User
    from app.models.product import Product
    from app.models.analytics import ModelMetric

    if not User.query.filter_by(email="admin@shopminer.com").first():
        admin = User(first_name="Admin", last_name="User", address="Admin Address",
                     email="admin@shopminer.com", role="admin", balance=1000000)
        admin.set_password("Admin@123")
        _db.session.add(admin)

    if not User.query.filter_by(email="customer@shopminer.com").first():
        customer = User(first_name="Test", last_name="Customer", address="123 Test St",
                        email="customer@shopminer.com", balance=500000)
        customer.set_password("Customer@123")
        _db.session.add(customer)

    if not User.query.filter_by(email="test@shopminer.com").first():
        test_user = User(first_name="Web", last_name="Test", address="Test Address",
                         email="test@shopminer.com", balance=500000)
        test_user.set_password("Test@123456")
        _db.session.add(test_user)

    if not Product.query.first():
        products = [
            Product(name="Test T-Shirt A", description="A test t-shirt", image="/img/tshirtA.webp", price=2999, stock=100, type="tshirt"),
            Product(name="Test Pants A", description="Test pants", image="/img/pantsA.jpg", price=5999, stock=50, type="pants"),
            Product(name="Test Socks A", description="Test socks", image="/img/sockA.webp", price=999, stock=200, type="sock"),
        ]
        _db.session.add_all(products)

    if not ModelMetric.query.first():
        seed_metrics = [
            ModelMetric(model_name="Clustering", metric_name="version", metric_value=0, detail="v4_optuna"),
            ModelMetric(model_name="Clustering", metric_name="K", metric_value=4, detail="4"),
            ModelMetric(model_name="Clustering", metric_name="silhouette_score", metric_value=0.36, detail="0.36"),
            ModelMetric(model_name="Churn", metric_name="version", metric_value=0, detail="v8_xgb_shap_K50"),
            ModelMetric(model_name="Churn", metric_name="test_auc", metric_value=0.77, detail="0.77"),
            ModelMetric(model_name="Churn", metric_name="oot_auc_mean", metric_value=0.91, detail="0.91"),
            ModelMetric(model_name="SalesForecast", metric_name="version", metric_value=0, detail="v3_calendar_features"),
            ModelMetric(model_name="SalesForecast", metric_name="best_smape", metric_value=4.86, detail="4.86%"),
            ModelMetric(model_name="Association", metric_name="version", metric_value=0, detail="v3_dual_level"),
            ModelMetric(model_name="Association", metric_name="global_rules_count", metric_value=694, detail="694"),
            ModelMetric(model_name="Association", metric_name="avg_lift", metric_value=11.07, detail="11.07"),
        ]
        _db.session.add_all(seed_metrics)

    _db.session.commit()

try:
    from waitress import serve
    serve(app, host="127.0.0.1", port=5000, threads=32)
except Exception as e:
    sys.stderr.write(f"Server error: {e}\n")
    sys.exit(1)
