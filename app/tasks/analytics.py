"""
Per-phase Celery tasks for analytics computation.
Imports Python functions directly from scripts instead of using subprocess.
"""
import sys
import os
import logging
from app.celery_app import celery

logger = logging.getLogger(__name__)

# Ensure project root is on sys.path for importing scripts/
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
# [GAP: missing-test] run_phase3_clustering needs Celery integration test env
def run_phase3_clustering(self):
    """Run Phase 3: K-Means customer clustering (RFM + behavioral features)."""
    from app import create_app
    from scripts.compute_analytics import _check_or_run_scripts, _load_pkl, _write_clustering

    app = create_app("development")
    with app.app_context():
        try:
            _check_or_run_scripts()
            phase3_data = _load_pkl("phase3_clusters_v3.pkl")
            _write_clustering(phase3_data)
            logger.info("Phase 3 clustering completed successfully")
            return {"status": "completed", "phase": "phase3_clustering"}
        except Exception as exc:
            logger.exception("Phase 3 clustering failed")
            raise self.retry(exc=exc)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
# [GAP: missing-test] run_phase4_churn needs Celery integration test env
def run_phase4_churn(self):
    """Run Phase 4: Customer churn prediction (LightGBM + CLV + NPW)."""
    from app import create_app
    from scripts.compute_analytics import _check_or_run_scripts, _load_pkl, _write_churn

    app = create_app("development")
    with app.app_context():
        try:
            _check_or_run_scripts()
            phase4_data = _load_pkl("phase4_churn_v5.pkl")
            _write_churn(phase4_data)
            logger.info("Phase 4 churn prediction completed successfully")
            return {"status": "completed", "phase": "phase4_churn"}
        except Exception as exc:
            logger.exception("Phase 4 churn prediction failed")
            raise self.retry(exc=exc)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
# [GAP: missing-test] run_phase5_forecast needs Celery integration test env
def run_phase5_forecast(self):
    """Run Phase 5: Sales forecast (weekly LightGBM with recent-sample weighting)."""
    from app import create_app
    from scripts.compute_analytics import _check_or_run_scripts, _load_pkl, _write_sales_prediction

    app = create_app("development")
    with app.app_context():
        try:
            _check_or_run_scripts()
            phase5_data = _load_pkl("phase5_forecast_v2.pkl")
            _write_sales_prediction(phase5_data)
            logger.info("Phase 5 sales forecast completed successfully")
            return {"status": "completed", "phase": "phase5_forecast"}
        except Exception as exc:
            logger.exception("Phase 5 sales forecast failed")
            raise self.retry(exc=exc)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
# [GAP: missing-test] run_phase6_association needs Celery integration test env
def run_phase6_association(self):
    """Run Phase 6: Association rule mining (Apriori, dual-level category + stockcode)."""
    from app import create_app
    from scripts.compute_analytics import _check_or_run_scripts, _load_pkl, _write_association

    app = create_app("development")
    with app.app_context():
        try:
            _check_or_run_scripts()
            phase6_data = _load_pkl("phase6_association_v2.pkl")
            _write_association(phase6_data)
            logger.info("Phase 6 association rules completed successfully")
            return {"status": "completed", "phase": "phase6_association"}
        except Exception as exc:
            logger.exception("Phase 6 association rules failed")
            raise self.retry(exc=exc)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
# [GAP: missing-test] run_compute_all needs Celery integration test env
def run_compute_all(self):
    """Orchestrator: run all analytics phases sequentially via compute_all()."""
    from app import create_app
    from scripts.compute_analytics import compute_all

    app = create_app("development")
    with app.app_context():
        try:
            compute_all(force=False)
            logger.info("Full analytics pipeline completed successfully")
            return {"status": "completed", "phase": "all"}
        except Exception as exc:
            logger.exception("Full analytics pipeline failed")
            raise self.retry(exc=exc)


@celery.task(bind=True, max_retries=3, default_retry_delay=60)
# [GAP: missing-test] compute_analytics_task needs Celery integration test env
def compute_analytics_task(self):
    """Backward-compatible: run full analytics pipeline (force clear old data).
    Replaces the old subprocess-based task.
    """
    from app import create_app
    from scripts.compute_analytics import compute_all

    app = create_app("development")
    with app.app_context():
        try:
            compute_all(force=True)
            logger.info("compute_analytics_task completed (force recompute)")
            return {"status": "completed"}
        except Exception as exc:
            logger.exception("compute_analytics_task failed")
            raise self.retry(exc=exc)


@celery.task(bind=True, max_retries=2, default_retry_delay=120)
# [GAP: missing-test] import_uci_data_task needs Celery integration test env
def import_uci_data_task(self):
    """Backward-compatible: import UCI Online Retail dataset.
    Replaces the old subprocess-based task.
    """
    from app import create_app
    from scripts.import_uci_data import import_uci_data

    app = create_app("development")
    with app.app_context():
        try:
            import_uci_data(force=False)
            logger.info("import_uci_data_task completed")
            return {"status": "completed"}
        except Exception as exc:
            logger.exception("import_uci_data_task failed")
            raise self.retry(exc=exc)
