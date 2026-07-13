"""Tests for app.services.analytics_service.

Covers key analytics functions: get_dashboard_stats, get_rfm_summary,
get_hot_products, get_churn_list, trigger_recompute, get_last_compute_time,
get_churn_trend, get_churn_importance, get_association_rules,
get_sales_trend, get_sales_prediction, get_product_recommendations,
get_user_rfm, get_user_trend, get_user_category_preference,
get_model_metrics, get_sales_heatmap, get_prediction_metrics,
get_model_viz, update_churn_status, update_user_rfm, _compute_segment,
require_admin.
"""

import json
import os
from datetime import datetime, timezone, date
from unittest.mock import mock_open, patch

import pytest
from app.extensions import db
from app.models.analytics import (
    ModelMetric, RFMAnalysis, SalesPrediction, AssociationRule,
    ChurnPrediction,
)
from app.models.order import Order, OrderItem
from app.models.product import Product
from app.models.user import User

pytestmark = pytest.mark.unit


class TestAnalyticsService:
    """Service-layer tests for analytics_service."""

    # ── get_dashboard_stats ──────────────────────────────────────

    def test_get_dashboard_stats_empty_db(self, app, analytics_service):
        """Dashboard stats with no data returns zeros."""
        stats = analytics_service.get_dashboard_stats()
        assert stats["total_users"] == 0
        assert stats["total_products"] == 0
        assert stats["total_orders"] == 0
        assert stats["total_revenue"] == 0
        assert stats["paid_orders"] == 0
        assert stats["churn_risk_count"] == 0
        assert stats["rfm_segments"] == []

    def test_get_dashboard_stats_with_data(self, app, analytics_service,
                                            sample_user, sample_product, sample_order):
        """Dashboard stats reflect seeded data."""
        stats = analytics_service.get_dashboard_stats()
        assert stats["total_users"] >= 1
        assert stats["total_products"] >= 1
        assert stats["total_orders"] >= 1

    # ── get_rfm_summary ──────────────────────────────────────────

    def test_get_rfm_summary_empty(self, app, analytics_service):
        """get_rfm_summary returns empty segments list when no RFM data."""
        result = analytics_service.get_rfm_summary()
        assert isinstance(result, dict)
        assert result["segments"] == []

    def test_get_rfm_summary_with_data(self, app, analytics_service, sample_user):
        """get_rfm_summary returns segments after creating an RFM record."""
        from app.models.analytics import RFMAnalysis
        rfm = RFMAnalysis(
            user_id=sample_user.id,
            recency=10, frequency=5, monetary=30000,
            r_score=4, f_score=3, m_score=4,
            rfm_score=11, segment="高价值客户",
        )
        db.session.add(rfm)
        db.session.commit()

        result = analytics_service.get_rfm_summary()
        assert len(result["segments"]) > 0
        seg = result["segments"][0]
        assert "segment" in seg
        assert "count" in seg

    # ── get_hot_products ─────────────────────────────────────────

    def test_get_hot_products_empty(self, app, analytics_service):
        """Hot products returns empty list when no products."""
        products = analytics_service.get_hot_products()
        assert isinstance(products, list)
        assert products == []

    def test_get_hot_products_with_data(self, app, analytics_service, sample_product):
        """Returns products after seeding one product."""
        products = analytics_service.get_hot_products()
        assert len(products) > 0
        assert products[0]["name"] == "Service Test Product"

    # ── get_churn_list ───────────────────────────────────────────

    def test_get_churn_list_empty(self, app, analytics_service):
        """get_churn_list returns empty predictions when no churn data."""
        result = analytics_service.get_churn_list()
        # Returns tuple: (predictions, total, pages, summary)
        predictions, total, pages, summary = result
        assert predictions == []
        assert total == 0

    # ── trigger_recompute ────────────────────────────────────────
    # NOTE: trigger_recompute is not tested here because it delegates to a
    # Celery task (app.tasks.compute_analytics_task) and Celery is not
    # installed in the test environment. The function signature is:
    #   trigger_recompute() -> {"status": "started", "task_id": "..."}
    # Testing it would require either Celery or mocking, and the task
    # instructions forbid mocking the service module.

    # ── get_last_compute_time ────────────────────────────────────

    def test_get_last_compute_time_returns_none(self, app, analytics_service):
        """get_last_compute_time returns None when no ModelMetric records exist."""
        result = analytics_service.get_last_compute_time()
        assert result is None

    def test_get_last_compute_time_with_metric(self, app, analytics_service):
        """get_last_compute_time returns an ISO string when a metric exists."""
        metric = ModelMetric(
            model_name="Churn",
            metric_name="test_auc",
            metric_value=0.85,
        )
        db.session.add(metric)
        db.session.commit()

        result = analytics_service.get_last_compute_time()
        assert isinstance(result, str)
        assert "T" in result  # ISO format includes 'T'

    # ── get_churn_trend ──────────────────────────────────────────

    def test_get_churn_trend_empty(self, app, analytics_service):
        """get_churn_trend returns bucket list with zero counts when no data."""
        trend = analytics_service.get_churn_trend()
        assert isinstance(trend, list)
        assert len(trend) > 0
        for bucket in trend:
            assert bucket["count"] == 0
            assert bucket["rate"] == 0

    # ── get_churn_importance ─────────────────────────────────────

    def test_get_churn_importance_empty(self, app, analytics_service):
        """get_churn_importance returns empty feature_counts when no data."""
        result = analytics_service.get_churn_importance()
        assert isinstance(result, dict)
        assert result["feature_counts"] == []
        assert result["total_risk"] == 0
        assert result["total_all"] == 0

    # ── get_association_rules ────────────────────────────────────

    def test_get_association_rules_empty(self, app, analytics_service):
        """get_association_rules returns pagination with no items when empty."""
        pagination = analytics_service.get_association_rules()
        assert pagination.total == 0
        assert pagination.items == []

    # ═══════════════════════════════════════════════════════════════
    # NEW TESTS for uncovered functions
    # ═══════════════════════════════════════════════════════════════

    # ── require_admin ─────────────────────────────────────────

    def test_require_admin_nonexistent_user(self, app, analytics_service):
        """[GAP: missing-test] require_admin returns None for non-existent user."""
        result = analytics_service.require_admin(99999)
        assert result is None

    def test_require_admin_non_admin(self, app, analytics_service, sample_user):
        """[GAP: missing-test] require_admin returns None for non-admin user."""
        result = analytics_service.require_admin(sample_user.id)
        assert result is None

    def test_require_admin_admin_user(self, app, analytics_service):
        """[GAP: missing-test] require_admin returns user for admin user."""
        admin = User(
            first_name="Real", last_name="Admin",
            email="realadmin@test.com", address="addr",
            role="admin",
        )
        admin.set_password("Admin123")
        db.session.add(admin)
        db.session.commit()

        result = analytics_service.require_admin(admin.id)
        assert result is not None
        assert result.role == "admin"

    # ── get_sales_trend ───────────────────────────────────────

    def test_get_sales_trend_empty(self, app, analytics_service):
        """[GAP: missing-test] get_sales_trend returns empty list when no data."""
        result = analytics_service.get_sales_trend()
        assert result == []

    def test_get_sales_trend_with_data(self, app, analytics_service,
                                        sample_user, sample_product):
        """[GAP: missing-test] get_sales_trend returns aggregated sales by date."""
        order = Order(
            user_id=sample_user.id, total_amount=5000,
            status=Order.STATUS_PAID,
            shipping_address="addr", shipping_phone="13800138000",
        )
        db.session.add(order)
        db.session.flush()
        item = OrderItem(order_id=order.id, product_id=sample_product.id,
                         quantity=1, unit_price=5000)
        db.session.add(item)
        db.session.commit()

        result = analytics_service.get_sales_trend()
        assert len(result) >= 1
        assert result[0].amount >= 5000
        assert result[0].count >= 1

    # ── get_sales_prediction ──────────────────────────────────

    def test_get_sales_prediction_empty(self, app, analytics_service):
        """[GAP: missing-test] get_sales_prediction returns empty when no data."""
        historical, monthly_preds = analytics_service.get_sales_prediction()
        assert historical == []
        assert monthly_preds == []

    def test_get_sales_prediction_with_data(self, app, analytics_service,
                                             sample_user, sample_product):
        """[GAP: missing-test] get_sales_prediction returns historical + predictions."""
        # Create a paid order (historical)
        order = Order(
            user_id=sample_user.id, total_amount=8000,
            status=Order.STATUS_PAID,
            shipping_address="addr", shipping_phone="13800138000",
        )
        db.session.add(order)
        db.session.flush()
        item = OrderItem(order_id=order.id, product_id=sample_product.id,
                         quantity=1, unit_price=8000)
        db.session.add(item)

        # Create a SalesPrediction
        pred = SalesPrediction(
            pred_date=date(2026, 1, 15),
            pred_amount=10000.0, pred_upper=12000.0, pred_lower=8000.0,
            model_name="LightGBM",
        )
        db.session.add(pred)
        db.session.commit()

        historical, monthly_preds = analytics_service.get_sales_prediction()
        assert len(historical) >= 1
        assert len(monthly_preds) >= 1
        first_pred = monthly_preds[0]
        assert "month" in first_pred
        assert first_pred["pred_amount"] >= 10000

    # ── get_product_recommendations ───────────────────────────

    def test_get_product_recommendations_empty(self, app, analytics_service,
                                                sample_product):
        """[GAP: missing-test] get_product_recommendations returns empty when no rules."""
        result = analytics_service.get_product_recommendations(sample_product.id)
        assert result == []

    def test_get_product_recommendations_with_data(self, app, analytics_service,
                                                     sample_product):
        """[GAP: missing-test] get_product_recommendations returns based on association rules."""
        # Second product for recommendation target
        other = Product(
            name="Recommended Item", description="Test",
            image="/img/rec.webp", price=1999, stock=10,
            type="tshirt", is_active=True,
        )
        db.session.add(other)
        db.session.flush()

        rule = AssociationRule(
            product_id=sample_product.id,
            antecedent="A", consequent="B",
            consequent_id=other.id,
            support=0.5, confidence=0.8, lift=1.5,
        )
        db.session.add(rule)
        db.session.commit()

        result = analytics_service.get_product_recommendations(sample_product.id)
        assert len(result) == 1
        assert result[0]["product"]["id"] == other.id
        assert result[0]["lift"] == 1.5

    def test_product_recommendations_skips_inactive(self, app, analytics_service,
                                                      sample_product):
        """[GAP: missing-test] get_product_recommendations skips inactive products."""
        other = Product(
            name="Inactive Rec", description="Test",
            image="/img/rec.webp", price=1999, stock=0,
            type="tshirt", is_active=False,
        )
        db.session.add(other)
        db.session.flush()

        rule = AssociationRule(
            product_id=sample_product.id,
            antecedent="A", consequent="B",
            consequent_id=other.id,
            support=0.5, confidence=0.8, lift=1.5,
        )
        db.session.add(rule)
        db.session.commit()

        result = analytics_service.get_product_recommendations(sample_product.id)
        assert result == []

    # ── get_user_rfm ──────────────────────────────────────────

    def test_get_user_rfm_nonexistent(self, app, analytics_service):
        """[GAP: missing-test] get_user_rfm returns None for user with no RFM data."""
        result = analytics_service.get_user_rfm(99999)
        assert result is None

    def test_get_user_rfm_with_data(self, app, analytics_service, sample_user):
        """[GAP: missing-test] get_user_rfm returns RFM analysis for the user."""
        rfm = RFMAnalysis(
            user_id=sample_user.id,
            recency=10, frequency=5, monetary=30000,
            r_score=4, f_score=3, m_score=4,
            rfm_score=11, segment="潜力客户",
        )
        db.session.add(rfm)
        db.session.commit()

        result = analytics_service.get_user_rfm(sample_user.id)
        assert result is not None
        assert result["my_segment"] == "潜力客户"
        assert "radar" in result
        assert "segment_distribution" in result
        assert "my_segment_advice" in result

    # ── get_user_trend ────────────────────────────────────────

    def test_get_user_trend_empty(self, app, analytics_service, sample_user):
        """[GAP: missing-test] get_user_trend returns empty list when no orders."""
        result = analytics_service.get_user_trend(sample_user.id)
        assert result == []

    def test_get_user_trend_with_data(self, app, analytics_service,
                                       sample_user, sample_product):
        """[GAP: missing-test] get_user_trend returns monthly aggregated data."""
        order = Order(
            user_id=sample_user.id, total_amount=5000,
            status=Order.STATUS_PAID,
            shipping_address="addr", shipping_phone="13800138000",
        )
        db.session.add(order)
        db.session.flush()
        item = OrderItem(order_id=order.id, product_id=sample_product.id,
                         quantity=1, unit_price=5000)
        db.session.add(item)
        db.session.commit()

        result = analytics_service.get_user_trend(sample_user.id)
        assert len(result) >= 1
        assert result[0].amount >= 5000

    # ── get_user_category_preference ──────────────────────────

    def test_get_user_category_preference_empty(self, app, analytics_service,
                                                  sample_user):
        """[GAP: missing-test] get_user_category_preference returns [] when no orders."""
        result = analytics_service.get_user_category_preference(sample_user.id)
        assert result == []

    def test_get_user_category_preference_with_data(self, app, analytics_service,
                                                      sample_user, sample_product):
        """[GAP: missing-test] get_user_category_preference returns category breakdown."""
        order = Order(
            user_id=sample_user.id, total_amount=2999,
            status=Order.STATUS_PAID,
            shipping_address="addr", shipping_phone="13800138000",
        )
        db.session.add(order)
        db.session.flush()
        item = OrderItem(order_id=order.id, product_id=sample_product.id,
                         quantity=1, unit_price=2999)
        db.session.add(item)
        db.session.commit()

        result = analytics_service.get_user_category_preference(sample_user.id)
        assert len(result) >= 1
        assert result[0]["category"] == sample_product.category_name
        assert result[0]["amount"] >= 2999

    def test_get_user_category_preference_skips_missing_product(
            self, app, analytics_service, sample_user, sample_product):
        """[GAP: missing-test] get_user_category_preference skips items with no product."""
        order = Order(
            user_id=sample_user.id, total_amount=1999,
            status=Order.STATUS_PAID,
            shipping_address="addr", shipping_phone="13800138000",
        )
        db.session.add(order)
        db.session.flush()
        # OrderItem referencing nonexistent product
        item = OrderItem(order_id=order.id, product_id=99999,
                         quantity=1, unit_price=1999)
        db.session.add(item)
        db.session.commit()

        # No error, just skips the unknown product
        result = analytics_service.get_user_category_preference(sample_user.id)
        assert result == []

    # ── get_model_metrics ─────────────────────────────────────

    def test_get_model_metrics_empty(self, app, analytics_service):
        """[GAP: missing-test] get_model_metrics returns empty dict when no metrics."""
        result = analytics_service.get_model_metrics()
        assert result == {}

    def test_get_model_metrics_with_data(self, app, analytics_service):
        """[GAP: missing-test] get_model_metrics returns grouped metrics."""
        m1 = ModelMetric(model_name="TestModel", metric_name="accuracy",
                         metric_value=0.95)
        m2 = ModelMetric(model_name="TestModel", metric_name="f1",
                         metric_value=0.93)
        db.session.add_all([m1, m2])
        db.session.commit()

        result = analytics_service.get_model_metrics()
        assert "TestModel" in result
        assert len(result["TestModel"]) == 2

    def test_get_model_metrics_filtered(self, app, analytics_service):
        """[GAP: missing-test] get_model_metrics filters by model_name."""
        m1 = ModelMetric(model_name="Alpha", metric_name="a", metric_value=1)
        m2 = ModelMetric(model_name="Beta", metric_name="b", metric_value=2)
        db.session.add_all([m1, m2])
        db.session.commit()

        result = analytics_service.get_model_metrics(model_name="Alpha")
        assert "Alpha" in result
        assert "Beta" not in result

    # ── get_sales_heatmap ─────────────────────────────────────

    def test_get_sales_heatmap_empty(self, app, analytics_service):
        """[GAP: missing-test] get_sales_heatmap returns empty structure when no data."""
        result = analytics_service.get_sales_heatmap()
        assert "months" in result
        assert "days" in result
        assert "data" in result
        assert result["months"] == []
        assert result["data"] == []

    def test_get_sales_heatmap_with_data(self, app, analytics_service,
                                          sample_user, sample_product):
        """[GAP: missing-test] get_sales_heatmap returns heatmap data with orders."""
        order = Order(
            user_id=sample_user.id, total_amount=5000,
            status=Order.STATUS_PAID,
            shipping_address="addr", shipping_phone="13800138000",
        )
        db.session.add(order)
        db.session.flush()
        item = OrderItem(order_id=order.id, product_id=sample_product.id,
                         quantity=1, unit_price=5000)
        db.session.add(item)
        db.session.commit()

        result = analytics_service.get_sales_heatmap()
        assert len(result["months"]) >= 1
        assert len(result["days"]) == 7  # Sun-Sat
        # Should have at least some data points
        assert len(result["data"]) >= 1

    # ── get_prediction_metrics ────────────────────────────────

    def test_get_prediction_metrics_empty(self, app, analytics_service):
        """[GAP: missing-test] get_prediction_metrics returns empty dict when no metrics."""
        result = analytics_service.get_prediction_metrics()
        assert result == {}

    def test_get_prediction_metrics_with_lightgbm(self, app, analytics_service):
        """[GAP: missing-test] get_prediction_metrics includes LightGBM_Weekly group."""
        smape = ModelMetric(
            model_name="SalesForecast", metric_name="best_smape",
            metric_value=4.86, detail="4.86%",
        )
        db.session.add(smape)
        db.session.commit()

        result = analytics_service.get_prediction_metrics()
        assert "LightGBM_Weekly" in result
        assert result["LightGBM_Weekly"]["best_smape"]["value"] == 4.86

    def test_get_prediction_metrics_with_prophet(self, app, analytics_service):
        """[GAP: missing-test] get_prediction_metrics includes Prophet group."""
        m = ModelMetric(
            model_name="Prophet", metric_name="mae",
            metric_value=200.0, detail="200",
        )
        db.session.add(m)
        db.session.commit()

        result = analytics_service.get_prediction_metrics()
        assert "Prophet" in result

    def test_get_prediction_metrics_with_sarima(self, app, analytics_service):
        """[GAP: missing-test] get_prediction_metrics includes SARIMA group."""
        m = ModelMetric(
            model_name="SARIMA", metric_name="mae",
            metric_value=150.0, detail="150",
        )
        db.session.add(m)
        db.session.commit()

        result = analytics_service.get_prediction_metrics()
        assert "SARIMA" in result

    # ── get_model_viz ─────────────────────────────────────────

    def test_get_model_viz_unknown_model(self, app, analytics_service):
        """[GAP: missing-test] get_model_viz returns None for unknown model name."""
        result = analytics_service.get_model_viz("unknown_model")
        assert result is None

    def test_get_model_viz_success(self, app, analytics_service):
        """[GAP: missing-test] get_model_viz returns parsed JSON when file exists."""
        viz_data = {"metadata": {"version": "v4"}, "charts": []}

        # Patch os.path.exists and builtins.open on the analytics_service module
        with patch.object(analytics_service.os.path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(viz_data))):
                result = analytics_service.get_model_viz("Clustering")
                assert result == viz_data

    def test_get_model_viz_read_error_returns_none(self, app, analytics_service):
        """[GAP: missing-test] get_model_viz returns None when file read fails."""
        with patch.object(analytics_service.os.path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data="invalid json content")):
                result = analytics_service.get_model_viz("Clustering")
                assert result is None

    def test_get_model_viz_phase4_alias(self, app, analytics_service):
        """[GAP: missing-test] get_model_viz maps Churn -> phase4."""
        viz_data = {"metadata": {"version": "v8"}, "data": []}
        with patch.object(analytics_service.os.path, "exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=json.dumps(viz_data))):
                result = analytics_service.get_model_viz("Churn")
                assert result == viz_data

    # ── update_churn_status ───────────────────────────────────

    def test_update_churn_status_not_found(self, app, analytics_service):
        """[GAP: missing-test] update_churn_status returns None when churn_id not found."""
        result = analytics_service.update_churn_status(99999, "contacted")
        assert result is None

    def test_update_churn_status_invalid(self, app, analytics_service, sample_user):
        """[GAP: missing-test] update_churn_status returns None for invalid status."""
        cp = ChurnPrediction(
            user_id=sample_user.id, churn_prob=0.7,
            is_churn_risk=True, status="pending",
        )
        db.session.add(cp)
        db.session.commit()

        result = analytics_service.update_churn_status(cp.id, "invalid_status")
        assert result is None

    def test_update_churn_status_valid(self, app, analytics_service, sample_user):
        """[GAP: missing-test] update_churn_status updates and returns the record."""
        cp = ChurnPrediction(
            user_id=sample_user.id, churn_prob=0.7,
            is_churn_risk=True, status="pending",
        )
        db.session.add(cp)
        db.session.commit()

        result = analytics_service.update_churn_status(cp.id, "contacted")
        assert result is not None
        assert result["status"] == "contacted"

        # Verify DB was committed
        updated = db.session.get(ChurnPrediction, cp.id)
        assert updated.status == "contacted"

    # ── update_user_rfm ───────────────────────────────────────

    def test_update_user_rfm_no_orders(self, app, analytics_service, sample_user):
        """[GAP: missing-test] update_user_rfm returns None when user has no valid orders."""
        result = analytics_service.update_user_rfm(sample_user.id)
        assert result is None

    def test_update_user_rfm_creates_new(self, app, analytics_service,
                                           sample_user, sample_product):
        """[GAP: missing-test] update_user_rfm creates a new RFM record."""
        order = Order(
            user_id=sample_user.id, total_amount=5000,
            status=Order.STATUS_PAID,
            shipping_address="addr", shipping_phone="13800138000",
        )
        db.session.add(order)
        db.session.flush()
        item = OrderItem(order_id=order.id, product_id=sample_product.id,
                         quantity=1, unit_price=5000)
        db.session.add(item)
        db.session.commit()

        analytics_service.update_user_rfm(sample_user.id)

        rfm = RFMAnalysis.query.filter_by(user_id=sample_user.id).first()
        assert rfm is not None
        assert rfm.monetary == 5000
        assert rfm.frequency == 1

    def test_update_user_rfm_updates_existing(self, app, analytics_service,
                                                sample_user, sample_product):
        """[GAP: missing-test] update_user_rfm updates existing RFM record."""
        # Pre-existing RFM
        rfm = RFMAnalysis(
            user_id=sample_user.id, recency=100, frequency=1,
            monetary=1000, r_score=1, f_score=1, m_score=1,
            rfm_score=3, segment="低价值客户",
        )
        db.session.add(rfm)
        db.session.commit()

        # New order
        order = Order(
            user_id=sample_user.id, total_amount=50000,
            status=Order.STATUS_PAID,
            shipping_address="addr", shipping_phone="13800138000",
        )
        db.session.add(order)
        db.session.flush()
        item = OrderItem(order_id=order.id, product_id=sample_product.id,
                         quantity=1, unit_price=50000)
        db.session.add(item)
        db.session.commit()

        analytics_service.update_user_rfm(sample_user.id)

        updated = db.session.get(RFMAnalysis, rfm.id)
        # monetary is RECALCULATED from orders (not accumulated)
        assert updated.monetary == 50000
        assert updated.frequency == 1  # only 1 order with valid status

    # ── _compute_segment ──────────────────────────────────────

    def test_compute_segment_high_value(self, analytics_service):
        """[GAP: missing-test] _compute_segment returns '高价值客户' for r>=4,f>=4,m>=4."""
        assert analytics_service._compute_segment(5, 5, 5) == "高价值客户"
        assert analytics_service._compute_segment(4, 4, 4) == "高价值客户"

    def test_compute_segment_potential(self, analytics_service):
        """[GAP: missing-test] _compute_segment returns '潜力客户' for r>=3,f>=3,m>=3."""
        assert analytics_service._compute_segment(3, 3, 3) == "潜力客户"
        assert analytics_service._compute_segment(3, 4, 3) == "潜力客户"

    def test_compute_segment_low_value(self, analytics_service):
        """[GAP: missing-test] _compute_segment returns '低价值客户' for r<=2,f<=2,m<=2."""
        assert analytics_service._compute_segment(1, 1, 1) == "低价值客户"
        assert analytics_service._compute_segment(2, 2, 2) == "低价值客户"

    def test_compute_segment_churn_warning(self, analytics_service):
        """[GAP: missing-test] _compute_segment returns '流失预警' for r<=2,f>=3."""
        assert analytics_service._compute_segment(1, 4, 3) == "流失预警"

    def test_compute_segment_general(self, analytics_service):
        """[GAP: missing-test] _compute_segment returns '一般客户' for other combos."""
        assert analytics_service._compute_segment(3, 2, 5) == "一般客户"
        assert analytics_service._compute_segment(2, 2, 3) == "一般客户"

    # ── get_churn_list edge cases ─────────────────────────────

    def test_get_churn_list_risk_only(self, app, analytics_service, sample_user):
        """[GAP: missing-test] get_churn_list with risk_only=True filters correctly."""
        cp_risk = ChurnPrediction(
            user_id=sample_user.id, churn_prob=0.9,
            is_churn_risk=True, status="pending",
        )
        db.session.add(cp_risk)
        db.session.commit()

        result = analytics_service.get_churn_list(risk_only=True)
        predictions, total, pages, summary = result
        assert total >= 1
        # Only risk items returned
        for p in predictions:
            assert p["churn_probability"] >= 0.5

    def test_get_churn_list_with_data(self, app, analytics_service, sample_user):
        """[GAP: missing-test] get_churn_list returns churn items with risk levels."""
        import json as _json
        cp = ChurnPrediction(
            user_id=sample_user.id, churn_prob=0.7,
            is_churn_risk=True, status="pending",
            top_features=_json.dumps(["monetary", "frequency"]),
        )
        db.session.add(cp)
        db.session.commit()

        result = analytics_service.get_churn_list()
        predictions, total, pages, summary = result
        assert total >= 1
        item = predictions[0]
        assert "churn_probability" in item
        assert "risk_level" in item
        assert "prediction_date" in item
        # 0.7 >= 0.5 (default optimal_threshold) -> medium
        assert item["risk_level"] == "medium"

    def test_get_churn_list_low_risk(self, app, analytics_service, sample_user):
        """[GAP: missing-test] get_churn_list returns 'low' risk for prob<optimal_threshold."""
        cp = ChurnPrediction(
            user_id=sample_user.id, churn_prob=0.3,
            is_churn_risk=False, status="pending",
        )
        db.session.add(cp)
        db.session.commit()

        result = analytics_service.get_churn_list()
        predictions, total, pages, summary = result
        assert total >= 1
        assert predictions[0]["risk_level"] == "low"

    # ── get_churn_trend with data ─────────────────────────────

    def test_get_churn_trend_with_data(self, app, analytics_service, sample_user):
        """[GAP: missing-test] get_churn_trend populates buckets when data exists."""
        cp_high = ChurnPrediction(
            user_id=sample_user.id, churn_prob=0.95,
            is_churn_risk=True, status="pending",
        )
        cp_mid = ChurnPrediction(
            user_id=sample_user.id, churn_prob=0.55,
            is_churn_risk=False, status="pending",
        )
        db.session.add_all([cp_high, cp_mid])
        db.session.commit()

        trend = analytics_service.get_churn_trend()
        assert len(trend) == 5  # 5 buckets
        high_bucket = [b for b in trend if b["bucket"] == "80-100%"][0]
        mid_bucket = [b for b in trend if b["bucket"] == "40-60%"][0]
        assert high_bucket["count"] >= 1
        assert mid_bucket["count"] >= 1
        assert high_bucket["rate"] > 0

    def test_get_churn_trend_prob_ge_one(self, app, analytics_service, sample_user):
        """[GAP: missing-test] get_churn_trend handles prob >= 1.0 in 80-100% bucket."""
        cp = ChurnPrediction(
            user_id=sample_user.id, churn_prob=1.0,
            is_churn_risk=True, status="pending",
        )
        db.session.add(cp)
        db.session.commit()

        trend = analytics_service.get_churn_trend()
        high_bucket = [b for b in trend if b["bucket"] == "80-100%"][0]
        assert high_bucket["count"] >= 1

    # ── get_churn_importance with data ────────────────────────

    def test_get_churn_importance_with_features(self, app, analytics_service):
        """[GAP: missing-test] get_churn_importance returns feature importance from metrics."""
        m1 = ModelMetric(
            model_name="Churn", metric_name="feature_importance_monetary",
            metric_value=85, detail="monetary",
        )
        m2 = ModelMetric(
            model_name="Churn", metric_name="feature_importance_frequency",
            metric_value=72, detail="frequency",
        )
        db.session.add_all([m1, m2])
        db.session.commit()

        result = analytics_service.get_churn_importance()
        assert len(result["feature_counts"]) >= 2
        # Features sorted by value desc
        assert result["feature_counts"][0]["count"] >= result["feature_counts"][1]["count"]

    # ── get_hot_products with category ────────────────────────

    def test_get_hot_products_with_category(self, app, analytics_service,
                                              sample_product):
        """[GAP: missing-test] get_hot_products filters by category."""
        result = analytics_service.get_hot_products(category=sample_product.category_name)
        assert len(result) >= 1
        assert result[0]["category_name"] == sample_product.category_name

    def test_get_hot_products_category_no_match(self, app, analytics_service):
        """[GAP: missing-test] get_hot_products returns [] for non-matching category."""
        result = analytics_service.get_hot_products(category="NonexistentCat")
        assert result == []

    # ── get_rfm_summary edge ──────────────────────────────────

    def test_get_rfm_summary_with_multiple_segments(self, app, analytics_service,
                                                      sample_user):
        """[GAP: missing-test] get_rfm_summary aggregates multiple RFM records."""
        from app.models.analytics import RFMAnalysis
        rfm1 = RFMAnalysis(
            user_id=sample_user.id,
            recency=10, frequency=5, monetary=30000,
            r_score=4, f_score=3, m_score=4,
            rfm_score=11, segment="高价值客户",
        )
        db.session.add(rfm1)
        rfm2 = RFMAnalysis(
            user_id=sample_user.id + 1 if hasattr(sample_user, 'id') else 2,
            recency=200, frequency=1, monetary=1000,
            r_score=1, f_score=1, m_score=1,
            rfm_score=3, segment="低价值客户",
        )
        # Create second user
        u2 = User(
            first_name="Second", last_name="User",
            email="second@test.com", address="addr",
        )
        u2.set_password("Pass1234")
        db.session.add(u2)
        db.session.flush()
        rfm2.user_id = u2.id
        db.session.add(rfm2)
        db.session.commit()

        result = analytics_service.get_rfm_summary()
        assert len(result["segments"]) >= 2
