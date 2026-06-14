"""Tests for app.services.analytics_service.

Covers key analytics functions: get_dashboard_stats, get_rfm_summary,
get_hot_products, get_churn_list, trigger_recompute, get_last_compute_time,
get_churn_trend, get_churn_importance, get_association_rules.
"""

import pytest
from app.extensions import db
from app.models.analytics import ModelMetric

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
