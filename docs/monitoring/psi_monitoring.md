# PSI (Population Stability Index) Drift Monitoring

> **Version**: 1.0  
> **Last updated**: 2026-06-15  
> **Applies to**: ShopMiner ML models (Clustering, Churn, Forecast, Association)

---

## Table of Contents

1. [What is PSI?](#what-is-psi)
2. [Why Monitor ML Model Drift?](#why-monitor-ml-model-drift)
3. [Architecture Overview](#architecture-overview)
4. [Installation & Setup](#installation--setup)
5. [Usage](#usage)
6. [Scheduling via Cron](#scheduling-via-cron)
7. [PSI Thresholds](#psi-thresholds)
8. [Interpretation Guide](#interpretation-guide)
9. [Per-Model Monitoring Details](#per-model-monitoring-details)
10. [What to Do When Drift Is Detected](#what-to-do-when-drift-is-detected)
11. [Alert Integration](#alert-integration)
12. [Troubleshooting](#troubleshooting)
13. [References](#references)

---

## What is PSI?

**Population Stability Index (PSI)** is a statistical measure that quantifies how much a distribution has shifted between two populations — a **baseline** (training data) and a **current** (production data) sample.

### Formula

```
PSI = Σ (P_i - Q_i) × ln(P_i / Q_i)
```

Where:

| Symbol | Meaning |
|--------|---------|
| `P_i`  | Proportion of baseline observations in bin *i* |
| `Q_i`  | Proportion of current observations in bin *i* |
| `i`    | Bins (deciles) across the feature's value range |

The feature space is divided into *k* equal-sized bins (typically deciles), and the proportion of observations falling into each bin is compared between the two populations. Higher PSI indicates greater distributional divergence.

### Why PSI for ML Models?

ML models are trained on historical data and make assumptions about the distribution of future inputs. When the production data distribution diverges from the training distribution, model performance degrades — a phenomenon known as **concept drift** or **covariate shift**. PSI provides an early warning signal before downstream metrics (revenue, accuracy, etc.) are visibly affected.

| Drift Type | Description | What PSI Detects |
|------------|-------------|------------------|
| **Covariate shift** | Input feature distributions change | ✅ Feature-level PSI |
| **Concept drift** | Relationship X→y changes | ❌ (requires performance monitoring) |
| **Prior probability shift** | Label distribution changes | ⚠️ Partially (probability PSI) |

---

## Why Monitor ML Model Drift?

ShopMiner's ML models power critical business decisions:

| Model | Business Impact | If Drifted |
|-------|----------------|------------|
| **Clustering (Phase 3)** | Customer segmentation, marketing targeting | Wrong segments → misallocated marketing spend |
| **Churn (Phase 4)** | Retention campaigns, at-risk customer identification | Missed churn signals → revenue loss |
| **Forecast (Phase 5)** | Inventory planning, staffing, cash flow | Over/under-stocking → lost sales or holding costs |
| **Association (Phase 6)** | Product recommendations, cross-sell | Irrelevant recommendations → lower conversion |

Regular PSI monitoring allows the team to **detect drift early**, **investigate root causes** (e.g., new product lines, seasonal shifts, data pipeline changes), and **trigger retraining** before business metrics degrade.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────┐
│                     Production Data                        │
│            (new pickle files in data/prep/)                 │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
┌──────────────────────────────────────────────────────────┐
│             monitor_psi.py                                 │
│                                                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │Phase 3   │  │Phase 4   │  │Phase 5   │  │Phase 6   │ │
│  │Clustering│  │Churn     │  │Forecast  │  │Association│ │
│  │RFM feats │  │Churn feats│  │Metric    │  │Support/   │ │
│  │PSI       │  │+ Prob PSI│  │delta PSI │  │Lift PSI  │ │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘ │
│       │              │              │              │       │
│       └──────────────┴──────────────┴──────────────┘       │
│                          │                                 │
│                    JSON Report                             │
│                    (stdout / file)                         │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │  Alerting /         │
              │  Dashboard / Logs   │
              └─────────────────────┘
```

### Data Flow

1. **Baseline** = training pickle files in `data/prep/` (created by Phase 2–6 scripts)
2. **Current** = production pickle files in a configurable directory (same structure)
3. **PSI** is calculated per-model using feature distributions extracted from pickle files
4. **Report** is emitted as structured JSON → consumed by alerting, dashboards, or CI/CD

---

## Installation & Setup

### Prerequisites

- **Python 3.10+**
- **Dependencies** (all already in `requirements.txt`):

| Package | Version | Used For |
|---------|---------|----------|
| `numpy` | ≥1.26 | Numerical arrays, histogram binning |
| `pandas` | ≥2.1 | Data loading from pickle files |

No additional dependencies are required beyond what ShopMiner already uses.

### Setup Steps

1. The script lives at `scripts/monitor_psi.py` — no installation needed.
2. Ensure baseline pickle files exist in `data/prep/`:

   | File | Source |
   |------|--------|
   | `phase2_preprocessed.pkl` | `scripts/phase2_preprocessing.py` |
   | `phase3_clusters_v3.pkl`  | `scripts/phase3_clustering_v3.py` |
   | `phase4_churn_v5.pkl`     | `scripts/phase4_churn_v5.py` |
   | `phase5_forecast_v2.pkl`  | `scripts/phase5_forecast_v2.py` |
   | `phase6_association_v2.pkl` | `scripts/phase6_association_v2.py` |

3. For production monitoring, set up a directory with current pickle files (either re-run the Phase scripts on new data, or copy the updated files).

---

## Usage

### Quick Self-Test

Verify the script works correctly by comparing baseline data against itself:

```bash
python scripts/monitor_psi.py --self-test
```

Expected output: all PSI values ≈ 0.0, `overall_status: "healthy"`.

### Basic Usage

Compare production data against baseline (both in `data/prep/`):

```bash
python scripts/monitor_psi.py
```

### Custom Directories

```bash
# Separate baseline and production directories
python scripts/monitor_psi.py \
    --baseline-dir /path/to/training/data/prep \
    --production-dir /path/to/production/data/prep
```

### Write Report to File

```bash
python scripts/monitor_psi.py \
    --output /var/log/psi/psi_report_$(date +\%Y\%m\%d).json
```

### Quiet Mode (JSON Only)

Useful for piping to downstream tools:

```bash
python scripts/monitor_psi.py --quiet
```

### Command-Line Arguments

| Argument | Type | Default | Description |
|----------|------|---------|-------------|
| `--baseline-dir` | path | `data/prep/` | Directory with baseline training pickle files |
| `--production-dir` | path | (same as baseline) | Directory with current production pickle files |
| `--self-test` | flag | `False` | Compare baseline against itself (validates script) |
| `--output` | path | `None` | Write JSON report to file instead of stdout |
| `--quiet` | flag | `False` | Suppress log output (print only JSON) |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All models healthy or only in warning state |
| `1` | At least one model has drifted (PSI > 0.25) |

---

## Scheduling via Cron

### Daily Monitoring (Recommended)

Run every day at 2:00 AM:

```cron
# ┌───────────── minute (0–59)
# │ ┌───────────── hour (0–23)
# │ │ ┌───────────── day of month (1–31)
# │ │ │ ┌───────────── month (1–12)
# │ │ │ │ ┌───────────── day of week (0–7, 0=Sun)
# │ │ │ │ │
0 2 * * * cd /path/to/ShopMiner && \
    python scripts/monitor_psi.py \
    --production-dir /path/to/production/data/prep \
    --output /var/log/psi/report_$(date +\%Y\%m\%d).json \
    --quiet >> /var/log/psi/monitor.log 2>&1
```

### Weekly Deep Check (Sunday)

```cron
0 3 * * 0 cd /path/to/ShopMiner && \
    python scripts/monitor_psi.py \
    --production-dir /path/to/production/data/prep \
    --output /var/log/psi/weekly_$(date +\%Y\%m\%d).json
```

### Cron Setup Instructions

#### Linux / macOS

```bash
# Edit crontab
crontab -e

# Add the daily monitoring line (from above)
```

#### Windows Task Scheduler

1. Open **Task Scheduler** → **Create Basic Task**
2. Name: `ShopMiner PSI Monitoring`
3. Trigger: **Daily** at 2:00 AM
4. Action: **Start a program**
   - Program: `python`
   - Arguments: `C:\Users\35027\Desktop\ShopMiner\scripts\monitor_psi.py --production-dir C:\path\to\production\prep --output C:\logs\psi\report_%date%.json --quiet`
   - Start in: `C:\Users\35027\Desktop\ShopMiner`

#### Docker / Containerised Deployments

Add to your `Dockerfile` or entrypoint script:

```bash
# Run monitoring after analytics computation
python scripts/compute_analytics.py && \
python scripts/monitor_psi.py --quiet
```

---

## PSI Thresholds

| PSI Range | Status | Meaning | Action Required |
|-----------|--------|---------|-----------------|
| **0.0 – 0.1** | ✅ **Stable** | Negligible distribution shift | None |
| **0.1 – 0.25** | ⚠️ **Warning** | Moderate shift detected | Investigate data changes |
| **> 0.25** | 🚨 **Drifted** | Significant shift, model at risk | Retrain model immediately |

### Threshold Rationale

These thresholds follow industry-standard practice (credit scoring, insurance underwriting):

- **0.0–0.1**: Normal variation inherent in sampling — no action needed.
- **0.1–0.25**: The distribution has shifted enough to warrant investigation. The model may still perform adequately, but the shift should be understood.
- **> 0.25**: A major distributional change that almost certainly degrades model performance. Retraining is strongly recommended.

> **Note**: These thresholds are conservative. For high-impact models (e.g., churn prediction for VIP customers), consider lowering the warning threshold to **0.15**.

---

## Interpretation Guide

### Sample Healthy Report

```json
{
  "timestamp": "2026-06-15T02:00:00",
  "overall_status": "healthy",
  "models": {
    "clustering": { "psi": 0.02, "status": "stable", ... },
    "churn": { "psi": 0.05, "status": "stable", ... },
    "forecast": { "psi": 0.03, "status": "stable", ... },
    "association": { "psi": 0.01, "status": "stable", ... }
  },
  "recommendation": "All models are stable. No action required."
}
```

→ **No action needed.** All distributions match baseline.

### Sample Warning Report

```json
{
  "timestamp": "2026-06-15T02:00:00",
  "overall_status": "warning",
  "models": {
    "churn": {
      "psi": 0.18,
      "status": "warning",
      "features": {
        "recency_days": { "psi": 0.22, "status": "warning" },
        "total_spent": { "psi": 0.15, "status": "warning" }
      }
    }
  },
  "recommendation": "Model churn is in warning range (0.1 < PSI ≤ 0.25). Investigate data changes."
}
```

→ **Investigation needed.** The churn model's feature distributions have shifted. Possible causes:
- Recent marketing campaign changed customer acquisition profile
- Seasonal variation in purchase behaviour
- Data pipeline issue (e.g., missing transactions)

**Next steps**:
1. Visualise the drifted features (`recency_days`, `total_spent`) to understand the shift direction
2. Check the churn model's prediction accuracy on a labelled holdout
3. Decide whether to retrain based on business impact

### Sample Drifted Report

```json
{
  "timestamp": "2026-06-15T02:00:00",
  "overall_status": "drifted",
  "models": {
    "forecast": {
      "psi": 0.30,
      "status": "drifted",
      "features": {
        "smape": { "baseline": 4.86, "current": 8.12, "ratio": 1.67, "psi_signal": 0.51, "status": "drifted" }
      }
    }
  },
  "recommendation": "Model forecast shows significant drift (PSI > 0.25). Consider retraining."
}
```

→ **Action required.** The forecast model's prediction error has nearly doubled (sMAPE 4.86% → 8.12%). Retrain the model with recent data.

---

## Per-Model Monitoring Details

### Phase 3 — Clustering (K-Means)

**Monitored Features** (7 RFM + behavioural):

| Feature | Description | Expected Range |
|---------|-------------|----------------|
| `recency_days` | Days since last purchase | 0–365+ |
| `total_orders` | Lifetime order count | 1–100+ |
| `total_spent` | Lifetime spend | 0–50,000+ |
| `unique_products` | Distinct products purchased | 1–500+ |
| `avg_spend_per_order` | Average order value | 0–5,000+ |
| `avg_items_per_order` | Average items per order | 1–100+ |
| `weekend_ratio` | Proportion of weekend purchases | 0.0–1.0 |

**Why these features**: These are the core inputs to the K-Means clustering model. Distribution shifts here would cause customers to be misclassified into wrong segments.

### Phase 4 — Churn (LightGBM)

**Monitored Features** (10 core churn features + prediction probability):

| Feature | Description | Expected Range |
|---------|-------------|----------------|
| `recency_days` | Days since last purchase | 0–365+ |
| `total_spent` | Lifetime spend | 0–50,000+ |
| `total_orders` | Lifetime order count | 1–100+ |
| `unique_products` | Distinct products purchased | 1–500+ |
| `avg_item_price` | Average item price | 0–100+ |
| `avg_purchase_hour` | Average purchase hour | 0–23 |
| `tenure_days` | Customer tenure | 0–1,000+ |
| `order_frequency` | Monthly order frequency | 0–30+ |
| `product_diversity` | Products / order | 0–100+ |
| `avg_spend_per_order` | Average order value | 0–5,000+ |
| `churn_probability` | Predicted churn probability | 0.0–1.0 |

**Prediction probability PSI**: Monitors whether the model's output distribution has shifted (e.g., more customers scoring high-risk than before).

### Phase 5 — Forecast (LightGBM Weekly)

**Monitored Metrics**:

| Metric | Description | What Shift Means |
|--------|-------------|------------------|
| `smape` | Symmetric MAPE | Forecast accuracy degrading |
| `mape` | Mean Absolute Percentage Error | Same, alternative view |
| `mae` | Mean Absolute Error | Absolute error increasing |
| `rmse` | Root Mean Squared Error | Larger errors / more variance |
| `residual_autocorr` | Residual autocorrelation | Model missing temporal patterns |
| `normality_p` | Residual normality p-value | Residual structure changing |

Since the forecast model's pickle does not contain raw weekly sales observations, the monitor compares model performance metrics. For a more granular check, extend the script to load the raw CSV and compute weekly revenue distribution PSI directly.

### Phase 6 — Association (Apriori)

**Monitored Distributions**:

| Distribution | Description | What Shift Means |
|--------------|-------------|------------------|
| Support values | Frequency of item sets | Purchase patterns changing |
| Lift values | Strength of association | Relationship between items changing |

The monitor extracts support and lift values from both the global (category-level) and stockcode-level rule sets and compares their distributions using PSI. A shift in support/lift distributions indicates that product co-purchase patterns have changed — suggesting the association rules need to be regenerated.

---

## What to Do When Drift Is Detected

### Decision Flowchart

```
PSI > 0.25 detected
        │
        ▼
  ┌─────────────────┐
  │ 1. Check data    │◄── Is this a data pipeline issue?
  │    pipeline      │    (e.g., missing records, encoding change)
  └────────┬────────┘
           │
           ▼
  ┌─────────────────┐
  │ 2. Investigate   │◄── What changed in the business?
  │    root cause    │    (e.g., new product line, seasonal shift,
  └────────┬────────┘     pricing change, new customer segment)
           │
           ▼
  ┌─────────────────┐
  │ 3. Assess impact  │◄── Validated model performance on holdout?
  │    on business   │    Run offline evaluation if labelled data exists
  └────────┬────────┘
           │
     ┌─────┴─────┐
     ▼           ▼
  Low impact   High impact
     │           │
     ▼           ▼
  Schedule    Retrain NOW
  retrain     (trigger compute_analytics.py)
```

### Step-by-Step Guide

#### 1. Check the Data Pipeline

- **Verify data freshness**: Is the production data up to date?
- **Check for missing values**: A sudden PSI spike can be caused by null values in a feature.
- **Look for encoding changes**: Did the data processing code change between baseline and production?
- **Validate record counts**: A sharp drop/increase in row count may indicate a ingestion issue.

#### 2. Investigate Business Root Cause

- **Seasonal effects**: Christmas, Black Friday, and summer sales can significantly shift distributions.
- **New product lines**: Added new categories? Customer purchase patterns will shift.
- **Marketing campaigns**: Promotions targeting specific segments will change feature distributions.
- **Pricing changes**: Price-sensitive features (`avg_spend_per_order`, `total_spent`) will drift.
- **Customer acquisition**: New customer demographics → distribution shift.

#### 3. Assess Business Impact

For the drifted model:

- **Retrospective evaluation**: If you have labelled production data, evaluate the model's accuracy on it.
- **Business metric monitoring**: Check dashboards for KPIs related to the model (e.g., churn rate, forecast error).
- **A/B test** (if feasible): Compare the current model vs. a freshly retrained version.

#### 4. Trigger Retraining

```bash
# Re-run the full analytics pipeline (regenerates pickle files)
cd /path/to/ShopMiner
python scripts/compute_analytics.py --force

# Verify drift is resolved
python scripts/monitor_psi.py --self-test
```

> **Note**: `compute_analytics.py` runs all Phase 3–6 scripts sequentially. For production, consider running individual Phase scripts to save time, or schedule the retraining during low-traffic hours.

### Retraining Decision Matrix

| Situation | Action | Priority |
|-----------|--------|----------|
| PSI > 0.25, critical model (churn/forecast) | Retrain immediately | 🔴 High |
| PSI > 0.25, non-critical model (clustering/association) | Retrain within 1 week | 🟡 Medium |
| 0.1 < PSI ≤ 0.25, any model | Investigate; retrain if verified impact | 🟢 Low |
| PSI ≤ 0.1 | No action | ✅ None |

---

## Alert Integration

### Email Alerts (sendmail / mailx)

```bash
# Run monitoring and email on drift
python scripts/monitor_psi.py --quiet > /tmp/psi_report.json
if [ $? -eq 1 ]; then
    cat /tmp/psi_report.json | \
    mail -s "🚨 ShopMiner ML Drift Alert" \
         -a "Content-Type: application/json" \
         ml-team@example.com
fi
```

### Slack Webhook Integration

```bash
#!/bin/bash
# psi_alert.sh — sends Slack notification on drift detection

WEBHOOK_URL="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXX"

python scripts/monitor_psi.py --quiet > /tmp/psi_report.json
EXIT_CODE=$?

if [ $EXIT_CODE -eq 1 ]; then
    PSI_JSON=$(cat /tmp/psi_report.json)
    DRIFTED=$(echo "$PSI_JSON" | python -c "
import sys, json
r = json.load(sys.stdin)
drifted = [(k, v['psi']) for k, v in r['models'].items() if v['status'] == 'drifted']
for name, psi in drifted:
    print(f'• *{name}*: PSI={psi:.3f}')
")
    curl -X POST -H 'Content-type: application/json' \
        --data "{
            \"text\": \"🚨 *ShopMiner ML Drift Detected*\n${DRIFTED}\n${r['recommendation']}\"
        }" "$WEBHOOK_URL"
fi
```

### Prometheus / Grafana

Expose PSI metrics via a Prometheus endpoint or push gateway:

```python
# Example: write Prometheus-friendly metrics
# (Add to monitor_psi.py or as a wrapper)
for model_name, model_data in report["models"].items():
    print(f"psi_{model_name}{{status=\"{model_data['status']}\"}} {model_data['psi']}")
```

Then scrape or push to Prometheus for Grafana dashboards.

### PagerDuty / Opsgenie

Use the exit code (`1` = drift) in your monitoring system:

```yaml
# Example: Datadog monitor configuration
alert:
  query: "exit_code(psi_monitor) == 1"
  message: "ShopMiner ML model drift detected — check psi_report.json"
  priority: P3
```

---

## Troubleshooting

| Problem | Likely Cause | Solution |
|---------|-------------|----------|
| `Baseline directory does not exist` | Wrong path or prep directory not created | Run `python scripts/compute_analytics.py` first |
| `File not found: phase2_preprocessed.pkl` | Preprocessing not run | Ensure `phase2_preprocessing.py` has executed |
| All PSI values are 0 | Same data used for baseline and current | Specify different `--production-dir` |
| `recursion depth` warning | XGBoost pickle version mismatch | Ignore (functionally harmless); upgrade XGBoost if annoying |
| High PSI on first run with production data | Normal initial drift | Compare distributions visually; establish baseline after retraining |
| JSON output is empty | Exit before print due to missing dir error | Check directory paths |

### Validation Checklist

Use this after setting up monitoring:

- [ ] Baseline pickle files exist in `data/prep/`
- [ ] `python scripts/monitor_psi.py --self-test` runs without errors
- [ ] Self-test output shows `"overall_status": "healthy"` and PSI ≈ 0
- [ ] Cron job syntax is valid (test with `crontab -l`)
- [ ] Slack/email webhook responds correctly (if configured)
- [ ] Output directory for report files exists and is writable
- [ ] Exit code handling is in place in monitoring pipeline

---

## References

- **Script**: `scripts/monitor_psi.py` — PSI calculation and monitoring logic
- **Data pipeline**: `scripts/compute_analytics.py` — orchestrates Phase 3–6 scripts
- **Feature engineering**: `scripts/phase2_preprocessing.py` — creates `phase2_preprocessed.pkl`
- **Clustering model**: `scripts/phase3_clustering_v3.py` — K-Means with RFM features
- **Churn model**: `scripts/phase4_churn_v5.py` — LightGBM churn prediction
- **Forecast model**: `scripts/phase5_forecast_v2.py` — LightGBM weekly sales forecast
- **Association model**: `scripts/phase6_association_v2.py` — Apriori association rules

### Further Reading

- [Population Stability Index — Wikipedia](https://en.wikipedia.org/wiki/Population_Stability_Index)
- [PSI in Credit Scoring — SAS](https://support.sas.com/resources/papers/proceedings15/3355-2015.pdf)
- [ML Model Monitoring Best Practices — Google](https://developers.google.com/machine-learning/testing-debugging/monitoring)
- [Why, When, and How to Retrain ML Models — Uber Engineering](https://eng.uber.com/retraining-ml-models/)
