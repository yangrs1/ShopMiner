"""
ShopMiner — PSI (Population Stability Index) Drift Monitoring Script

Monitors feature distribution drift across all four ML models:
  - Phase 3 (Clustering/K-Means):  RFM + behavioral feature PSI
  - Phase 4 (Churn/LightGBM):      Churn feature + prediction probability PSI
  - Phase 5 (Forecast/LightGBM):   Sales trend distribution PSI
  - Phase 6 (Association/Apriori): Product occurrence frequency PSI

Usage:
    # Compare current production data (in data/prep/) against baseline training data
    python scripts/monitor_psi.py

    # Explicitly specify baseline and production data directories
    python scripts/monitor_psi.py --baseline-dir data/prep/baseline --production-dir data/prep/production

    # Self-check (compare baseline against itself – PSI ~ 0)
    python scripts/monitor_psi.py --self-test

Output:
    Structured JSON report to stdout. Exit code:
      0 = healthy / warning
      1 = drifted (PSI > 0.25 for any model)
"""

import sys
import os
import json
import logging
import argparse
from datetime import datetime, timezone

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)
DEFAULT_PREP_DIR = os.path.join(PROJECT_ROOT, "data", "prep")

BASELINE_FILES = {
    "phase2": "phase2_preprocessed.pkl",
    "phase3": "phase3_clusters_v3.pkl",
    "phase4": "phase4_churn_v5.pkl",
    "phase5": "phase5_forecast_v2.pkl",
    "phase6": "phase6_association_v2.pkl",
}

# Phase 3: RFM + behavioural features used by the clustering model
CLUSTER_MONITOR_FEATURES = [
    "recency_days",
    "total_orders",
    "total_spent",
    "unique_products",
    "avg_spend_per_order",
    "avg_items_per_order",
    "weekend_ratio",
]

# Phase 4: Top-K churn features to monitor (subset of the 50 features)
CHURN_MONITOR_FEATURES = [
    "recency_days",
    "total_spent",
    "total_orders",
    "unique_products",
    "avg_item_price",
    "avg_purchase_hour",
    "tenure_days",
    "order_frequency",
    "product_diversity",
    "avg_spend_per_order",
]

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("monitor_psi")


# ===================================================================
#  PSI Calculation
# ===================================================================
def calculate_psi(baseline: np.ndarray, current: np.ndarray, n_bins: int = 10) -> float:
    """
    Compute Population Stability Index between two 1-D distributions.

    PSI = sum((P_i - Q_i) * ln(P_i / Q_i))

    Parameters
    ----------
    baseline : array-like
        Reference distribution (training period).
    current  : array-like
        Production distribution to evaluate.
    n_bins   : int
        Number of bins to discretise the range (default 10).

    Returns
    -------
    psi : float
        PSI value. 0 = identical distributions.
    """
    # Drop NaN / inf
    baseline = np.asarray(baseline, dtype=np.float64)
    current = np.asarray(current, dtype=np.float64)
    baseline = baseline[~np.isnan(baseline) & ~np.isinf(baseline)]
    current = current[~np.isnan(current) & ~np.isinf(current)]

    if len(baseline) == 0 or len(current) == 0:
        logger.warning("Empty array passed to calculate_psi — returning 0.0")
        return 0.0

    # Determine bin edges from the combined range
    combined = np.concatenate([baseline, current])
    if combined.std() < 1e-12:
        return 0.0  # constant feature

    # Use percentiles of baseline for bin edges
    # (adding tiny jitter avoids ties at boundaries)
    edges = np.percentile(baseline, np.linspace(0, 100, n_bins + 1))
    # Ensure unique edges (merge duplicates)
    edges = np.unique(edges)
    if len(edges) < 2:
        return 0.0

    # Count proportions
    p_baseline = np.histogram(baseline, bins=edges)[0].astype(np.float64)
    p_current = np.histogram(current, bins=edges)[0].astype(np.float64)

    # Convert to proportions and clip to avoid log(0) / div by 0
    p_baseline = p_baseline / p_baseline.sum()
    p_current = p_current / p_current.sum()

    # Epsilon smoothing for zero bins
    EPS = 1e-6
    p_baseline = np.clip(p_baseline, EPS, 1.0)
    p_current = np.clip(p_current, EPS, 1.0)

    psi = np.sum((p_baseline - p_current) * np.log(p_baseline / p_current))
    return float(psi)


# ===================================================================
#  Data Loaders
# ===================================================================
def _load_pkl(filepath: str, label: str = ""):
    """Safely load a pickle file and return the dict (or empty dict on failure)."""
    if not os.path.exists(filepath):
        logger.warning("File not found: %s (%s)", filepath, label)
        return {}
    try:
        with open(filepath, "rb") as f:
            import pickle
            data = pickle.load(f)
        logger.info("Loaded: %s (%s)", os.path.basename(filepath), label)
        return data
    except Exception as exc:
        logger.error("Failed to load %s (%s): %s", filepath, label, exc)
        return {}


def _psi_status(psi: float) -> str:
    """Classify PSI value into stable / warning / drifted."""
    if psi <= 0.1:
        return "stable"
    elif psi <= 0.25:
        return "warning"
    else:
        return "drifted"


# ===================================================================
#  Phase 3 – Clustering (RFM + behavioural feature drift)
# ===================================================================
def monitor_clustering(
    baseline_features: pd.DataFrame,
    current_features: pd.DataFrame,
) -> dict:
    """
    Compare feature distributions for the K-Means clustering model.

    Monitoring: 7 core RFM + behavioural features.
    """
    results: dict = {"psi": 0.0, "status": "stable", "features": {}}

    if baseline_features is None or current_features is None:
        logger.warning("Skipping clustering PSI — missing feature data")
        return results

    psi_values = []
    for feature in CLUSTER_MONITOR_FEATURES:
        if feature not in baseline_features.columns or feature not in current_features.columns:
            logger.warning("Feature '%s' not found — skipping", feature)
            continue

        base_vals = baseline_features[feature].values
        curr_vals = current_features[feature].values
        psi = calculate_psi(base_vals, curr_vals)
        results["features"][feature] = {
            "psi": round(psi, 6),
            "status": _psi_status(psi),
        }
        psi_values.append(psi)

    if psi_values:
        avg_psi = float(np.mean(psi_values))
        results["psi"] = round(avg_psi, 6)
        results["status"] = _psi_status(avg_psi)

    return results


# ===================================================================
#  Phase 4 – Churn (feature + prediction probability drift)
# ===================================================================
def monitor_churn(
    baseline_churn_data: dict,
    current_churn_data: dict,
    baseline_features: pd.DataFrame,
    current_features: pd.DataFrame,
) -> dict:
    """
    Monitor churn model feature distributions and prediction probabilities.

    - Feature drift on top-10 churn features
    - Probability distribution drift if churn probabilities are available
    """
    results: dict = {"psi": 0.0, "status": "stable", "features": {}}

    if baseline_features is None or current_features is None:
        logger.warning("Skipping churn PSI — missing feature data")
        return results

    # --- Feature distribution PSI ---
    psi_values = []
    for feature in CHURN_MONITOR_FEATURES:
        if feature not in baseline_features.columns or feature not in current_features.columns:
            logger.warning("Churn feature '%s' not found — skipping", feature)
            continue

        base_vals = baseline_features[feature].values
        curr_vals = current_features[feature].values
        psi = calculate_psi(base_vals, curr_vals)
        results["features"][feature] = {
            "psi": round(psi, 6),
            "status": _psi_status(psi),
        }
        psi_values.append(psi)

    # --- Prediction probability PSI ---
    base_probs = baseline_churn_data.get("churn_probabilities", None)
    curr_probs = current_churn_data.get("churn_probabilities", None)
    # Fallback: try probability-group column from features_df
    if base_probs is None and "churn_prob_group" in baseline_features.columns:
        # Map probability-group labels to approximate numeric values
        prob_map = {"active": 0.05, "cool": 0.20, "warm": 0.40, "at-risk": 0.65, "churned": 0.85}
        base_probs = baseline_features["churn_prob_group"].map(prob_map).values
        curr_probs = current_features["churn_prob_group"].map(prob_map).values

    if base_probs is not None and curr_probs is not None:
        base_probs_arr = np.asarray(base_probs, dtype=np.float64)
        curr_probs_arr = np.asarray(curr_probs, dtype=np.float64)
        base_probs_arr = base_probs_arr[~np.isnan(base_probs_arr)]
        curr_probs_arr = curr_probs_arr[~np.isnan(curr_probs_arr)]
        if len(base_probs_arr) > 0 and len(curr_probs_arr) > 0:
            psi_prob = calculate_psi(base_probs_arr, curr_probs_arr)
            results["features"]["churn_probability"] = {
                "psi": round(psi_prob, 6),
                "status": _psi_status(psi_prob),
            }
            psi_values.append(psi_prob)

    if psi_values:
        avg_psi = float(np.mean(psi_values))
        results["psi"] = round(avg_psi, 6)
        results["status"] = _psi_status(avg_psi)

    return results


# ===================================================================
#  Phase 5 – Forecast (weekly sales trend distribution drift)
# ===================================================================
def monitor_forecast(
    baseline_forecast_data: dict,
    current_forecast_data: dict,
) -> dict:
    """
    Monitor weekly sales trend distributions.

    Compares the distribution of weekly revenue (LineTotal sum) between
    baseline and current periods.
    """
    results: dict = {"psi": 0.0, "status": "stable", "features": {}}

    # No per-feature data in forecast pickles; derive from audit or fallback
    # If the pickles contain a full results dict, we check sales metrics
    if not baseline_forecast_data and not current_forecast_data:
        logger.warning("Skipping forecast PSI — no data available")
        return results

    # Compare key forecast metrics as a proxy for distribution shift
    # (Actual weekly sales data is in the raw CSV; here we compare
    #  model performance metrics as a lightweight signal)
    metrics_pairs = [
        ("test_smape", "smape"),
        ("test_mape", "mape"),
        ("test_mae", "mae"),
        ("test_rmse", "rmse"),
    ]
    psi_values = []

    for base_key, label in metrics_pairs:
        base_val = baseline_forecast_data.get(base_key, None)
        curr_val = current_forecast_data.get(base_key, None)
        if base_val is not None and curr_val is not None:
            # For scalar metrics we compute a simplified relative shift
            # (not a true PSI, but a practical delta for a single value)
            eps = 1e-6
            ratio = (float(curr_val) + eps) / (float(base_val) + eps)
            # Convert ratio to a pseudo-PSI: symmetric log-scaled shift
            pseudo_psi = abs(np.log(ratio))
            results["features"][label] = {
                "baseline": round(float(base_val), 4),
                "current": round(float(curr_val), 4),
                "ratio": round(float(ratio), 4),
                "psi_signal": round(pseudo_psi, 6),
                "status": _psi_status(pseudo_psi),
            }
            psi_values.append(pseudo_psi)

    # Also check audit residual statistics if available
    for audit_key in ["residual_autocorr", "normality_p"]:
        base_val = baseline_forecast_data.get("audit", {}).get(audit_key, None)
        curr_val = current_forecast_data.get("audit", {}).get(audit_key, None)
        if base_val is not None and curr_val is not None:
            delta = abs(float(curr_val) - float(base_val))
            pseudo_psi = min(delta * 5, 1.0)  # scale to ~PSI range
            results["features"][f"audit_{audit_key}"] = {
                "baseline": round(float(base_val), 4),
                "current": round(float(curr_val), 4),
                "psi_signal": round(pseudo_psi, 6),
                "status": _psi_status(pseudo_psi),
            }
            psi_values.append(pseudo_psi)

    if psi_values:
        avg_psi = float(np.mean(psi_values))
        results["psi"] = round(avg_psi, 6)
        results["status"] = _psi_status(avg_psi)

    return results


# ===================================================================
#  Phase 6 – Association (product occurrence frequency drift)
# ===================================================================
def monitor_association(
    baseline_assoc_data: dict,
    current_assoc_data: dict,
) -> dict:
    """
    Monitor product occurrence frequency distribution.

    Compares the distribution of 'support' values across association rules
    between baseline and current periods.
    """
    results: dict = {"psi": 0.0, "status": "stable", "features": {}}

    if not baseline_assoc_data and not current_assoc_data:
        logger.warning("Skipping association PSI — no data available")
        return results

    def _extract_supports(data: dict, source: str) -> list:
        """Extract support values from rule lists embedded in the pickle."""
        supports = []
        # Global rules
        gr = data.get("global_rules", {})
        if isinstance(gr, dict):
            top_rules = gr.get("top_rules", [])
        elif isinstance(gr, list):
            top_rules = gr
        else:
            top_rules = []
        for rule in top_rules:
            s = rule.get("support", None)
            if s is not None:
                supports.append(float(s))

        # Stockcode-level rules
        sr = data.get("stockcode_rules", {})
        if isinstance(sr, dict):
            top_sr = sr.get("top_rules", [])
        elif isinstance(sr, list):
            top_sr = sr
        else:
            top_sr = []
        for rule in top_sr:
            s = rule.get("support", None)
            if s is not None:
                supports.append(float(s))

        logger.info("Association: extracted %d support values from %s", len(supports), source)
        return supports

    base_supports = _extract_supports(baseline_assoc_data, "baseline")
    curr_supports = _extract_supports(current_assoc_data, "current")

    if not base_supports or not curr_supports:
        logger.warning("Insufficient support values for association PSI")
        return results

    # PSI on support distribution
    psi_support = calculate_psi(np.array(base_supports), np.array(curr_supports))
    results["features"]["support_distribution"] = {
        "n_baseline_rules": len(base_supports),
        "n_current_rules": len(curr_supports),
        "psi": round(psi_support, 6),
        "status": _psi_status(psi_support),
    }

    # Also check lift distribution
    def _extract_lifts(data: dict, source: str) -> list:
        lifts = []
        gr = data.get("global_rules", {})
        if isinstance(gr, dict):
            top_rules = gr.get("top_rules", [])
        elif isinstance(gr, list):
            top_rules = gr
        else:
            top_rules = []
        for rule in top_rules:
            l = rule.get("lift", None)
            if l is not None:
                lifts.append(float(l))
        logger.info("Association: extracted %d lift values from %s", len(lifts), source)
        return lifts

    base_lifts = _extract_lifts(baseline_assoc_data, "baseline")
    curr_lifts = _extract_lifts(current_assoc_data, "current")

    if len(base_lifts) >= 5 and len(curr_lifts) >= 5:
        psi_lift = calculate_psi(np.array(base_lifts), np.array(curr_lifts))
        results["features"]["lift_distribution"] = {
            "n_baseline_rules": len(base_lifts),
            "n_current_rules": len(curr_lifts),
            "psi": round(psi_lift, 6),
            "status": _psi_status(psi_lift),
        }
        avg_psi = float(np.mean([psi_support, psi_lift]))
    else:
        avg_psi = psi_support

    results["psi"] = round(avg_psi, 6)
    results["status"] = _psi_status(avg_psi)
    return results


# ===================================================================
#  Main Entry Point
# ===================================================================
def build_recommendation(models: dict) -> str:
    """Generate a human-readable recommendation based on model statuses."""
    drifted = [name for name, m in models.items() if m.get("status") == "drifted"]
    warnings = [name for name, m in models.items() if m.get("status") == "warning"]

    if not drifted and not warnings:
        return "All models are stable. No action required."
    parts = []
    if drifted:
        parts.append(
            "Model{} {} show{} significant drift (PSI > 0.25). "
            "Consider retraining.".format(
                "s" if len(drifted) > 1 else "",
                ", ".join(drifted),
                "" if len(drifted) > 1 else "s",
            )
        )
    if warnings:
        parts.append(
            "Model{} {} {} in warning range (0.1 < PSI ≤ 0.25). "
            "Investigate data changes.".format(
                "s" if len(warnings) > 1 else "",
                ", ".join(warnings),
                "are" if len(warnings) > 1 else "is",
            )
        )
    return " ".join(parts)


def run_psi_monitoring(
    baseline_dir: str,
    production_dir: str,
    self_test: bool = False,
) -> dict:
    """
    Execute the full PSI monitoring pipeline.

    Parameters
    ----------
    baseline_dir  : path to baseline (training) pickle files
    production_dir: path to current production pickle files
    self_test     : if True, use baseline_dir for both (PSI ≈ 0 check)

    Returns
    -------
    report : dict ready for JSON serialisation
    """
    logger.info("=" * 60)
    logger.info("PSI Drift Monitoring")
    logger.info("Baseline dir:   %s", baseline_dir)
    logger.info("Production dir: %s", production_dir)
    logger.info("Self-test:      %s", self_test)
    logger.info("=" * 60)

    current_dir = baseline_dir if self_test else production_dir

    # ------------------------------------------------------------------
    # 1. Load baseline data
    # ------------------------------------------------------------------
    logger.info("\n[1/6] Loading baseline data ...")
    base_p2 = _load_pkl(os.path.join(baseline_dir, BASELINE_FILES["phase2"]), "baseline-phase2")
    base_p3 = _load_pkl(os.path.join(baseline_dir, BASELINE_FILES["phase3"]), "baseline-phase3")
    base_p4 = _load_pkl(os.path.join(baseline_dir, BASELINE_FILES["phase4"]), "baseline-phase4")
    base_p5 = _load_pkl(os.path.join(baseline_dir, BASELINE_FILES["phase5"]), "baseline-phase5")
    base_p6 = _load_pkl(os.path.join(baseline_dir, BASELINE_FILES["phase6"]), "baseline-phase6")

    base_features_df = base_p2.get("features_df") if base_p2 else None

    # ------------------------------------------------------------------
    # 2. Load current (production) data
    # ------------------------------------------------------------------
    logger.info("\n[2/6] Loading production data ...")
    curr_p2 = _load_pkl(os.path.join(current_dir, BASELINE_FILES["phase2"]), "production-phase2")
    curr_p3 = _load_pkl(os.path.join(current_dir, BASELINE_FILES["phase3"]), "production-phase3")
    curr_p4 = _load_pkl(os.path.join(current_dir, BASELINE_FILES["phase4"]), "production-phase4")
    curr_p5 = _load_pkl(os.path.join(current_dir, BASELINE_FILES["phase5"]), "production-phase5")
    curr_p6 = _load_pkl(os.path.join(current_dir, BASELINE_FILES["phase6"]), "production-phase6")

    curr_features_df = curr_p2.get("features_df") if curr_p2 else None

    # ------------------------------------------------------------------
    # 3–6. Per-model PSI calculation
    # ------------------------------------------------------------------
    logger.info("\n[3/6] Clustering PSI ...")
    clustering = monitor_clustering(base_features_df, curr_features_df)

    logger.info("\n[4/6] Churn PSI ...")
    churn = monitor_churn(base_p4, curr_p4, base_features_df, curr_features_df)

    logger.info("\n[5/6] Forecast PSI ...")
    forecast = monitor_forecast(base_p5, curr_p5)

    logger.info("\n[6/6] Association PSI ...")
    association = monitor_association(base_p6, curr_p6)

    # ------------------------------------------------------------------
    # Build report
    # ------------------------------------------------------------------
    models = {
        "clustering": clustering,
        "churn": churn,
        "forecast": forecast,
        "association": association,
    }

    statuses = [m.get("status", "unknown") for m in models.values()]
    if "drifted" in statuses:
        overall_status = "drifted"
    elif "warning" in statuses:
        overall_status = "warning"
    else:
        overall_status = "healthy"

    report = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S"),
        "overall_status": overall_status,
        "baseline_dir": baseline_dir,
        "production_dir": current_dir,
        "models": models,
        "recommendation": build_recommendation(models),
    }

    return report


def parse_args(argv: list = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="ShopMiner PSI Drift Monitoring",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--baseline-dir",
        default=DEFAULT_PREP_DIR,
        help=f"Directory containing baseline pickle files (default: {DEFAULT_PREP_DIR})",
    )
    parser.add_argument(
        "--production-dir",
        default=None,
        help="Directory containing current production pickle files (default: same as --baseline-dir)",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Compare baseline against itself (PSI ~ 0, validates the script works)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to write JSON report to a file instead of stdout",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress log output (only print JSON report)",
    )
    return parser.parse_args(argv)


def main():
    args = parse_args()

    if args.quiet:
        logging.getLogger("monitor_psi").disabled = True

    baseline_dir = os.path.abspath(args.baseline_dir)
    production_dir = (
        os.path.abspath(args.production_dir) if args.production_dir else baseline_dir
    )

    # Validate directories exist
    if not os.path.isdir(baseline_dir):
        logger.error("Baseline directory does not exist: %s", baseline_dir)
        sys.exit(1)
    if not args.self_test and not os.path.isdir(production_dir):
        logger.error("Production directory does not exist: %s", production_dir)
        sys.exit(1)

    report = run_psi_monitoring(
        baseline_dir=baseline_dir,
        production_dir=production_dir,
        self_test=args.self_test,
    )

    # Output report
    json_str = json.dumps(report, indent=2, ensure_ascii=False)
    if args.output:
        output_path = os.path.abspath(args.output)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(json_str)
        logger.info("Report written to: %s", output_path)
    else:
        print(json_str)

    # Exit code signalling
    if report["overall_status"] == "drifted":
        logger.warning("Drift detected — exiting with code 1")
        sys.exit(1)
    else:
        logger.info("Status: %s — exiting with code 0", report["overall_status"])
        sys.exit(0)


if __name__ == "__main__":
    main()
