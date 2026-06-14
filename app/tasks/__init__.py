"""
Celery tasks package.
Re-exports all tasks from analytics module for backward-compatible imports.
Uses lazy loading via __getattr__ so importing this package does not
require celery to be installed (important for test environments).
"""
import importlib

_TASK_NAMES = [
    "run_phase3_clustering",
    "run_phase4_churn",
    "run_phase5_forecast",
    "run_phase6_association",
    "run_compute_all",
    "compute_analytics_task",
    "import_uci_data_task",
]

__all__ = list(_TASK_NAMES)


def __getattr__(name):
    if name in _TASK_NAMES:
        module = importlib.import_module("app.tasks.analytics")
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
