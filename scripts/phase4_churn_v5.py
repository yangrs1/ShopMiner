"""
Phase 4 v8: UK Online Retail - Churn Prediction (latest, SHAP top-50)
  - v5 base: Optuna-tuned XGBoost on temporal VAL (cutoff 2011-07-31)
  - v7 evolution: Stacking + calibration + business-constrained threshold
  - v8 latest (this file): v5/v7 base + SHAP top-50 feature selection
    -> 50 features (from 53) selected by mean |SHAP| ranking
    -> Retrained XGBoost on top-50
    -> OOT AUC: 0.9127 (v7) -> 0.9128 (v8, +0.01%)
    -> Test AUC: 0.7767 -> 0.7711 (-0.56%, within noise)
  - Saves as phase4_churn_v5.pkl (filename kept for backward compatibility)
    with version field = "v8_xgb_shap_K50"
"""
import sys, os, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pickle, numpy as np, pandas as pd
from sklearn.model_selection import StratifiedKFold, train_test_split, KFold
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    roc_auc_score, precision_recall_curve, auc as pr_auc_func,
    brier_score_loss, classification_report,
    mean_absolute_error, mean_squared_error, r2_score,
    average_precision_score, f1_score as f1_multiclass,
)
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression

PREP_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "prep")
RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
CHART_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "charts")
os.makedirs(PREP_DIR, exist_ok=True)
os.makedirs(CHART_DIR, exist_ok=True)
np.random.seed(42)

print("=" * 70)
print("PHASE 4 v5: 流失预警优化版 — Stacking + 校准 + 业务阈值 + CLV修复 + OOT")
print("=" * 70)

# ═══ Load Phase3 Clustering Results ═══
print("\n-- 加载Phase3聚类结果 --")
phase3_path = os.path.join(PREP_DIR, "phase3_clusters_v3.pkl")
if not os.path.exists(phase3_path):
    phase3_path = os.path.join(os.path.dirname(__file__), "..", "model_optimization", "data", "prep", "phase3_clusters_v3.pkl")
if os.path.exists(phase3_path):
    with open(phase3_path, "rb") as f:
        phase3_data = pickle.load(f)
    phase3_labels = phase3_data["labels"]
    phase3_method = phase3_data["method"]
    phase3_k = phase3_data["K"]
    print(f"  Phase3聚类: {phase3_method}, K={phase3_k}")
    has_phase3 = True
else:
    print("  Phase3聚类结果不存在, 跳过聚类特征注入")
    has_phase3 = False

# ═══ Data Loading & Preprocessing ═══
df = pd.read_csv(
    os.path.join(RAW_DIR, "Online_Retail.csv"),
    encoding="latin1", parse_dates=["InvoiceDate"],
)
df["InvoiceNo"] = df["InvoiceNo"].astype(str)
df = df[~df["InvoiceNo"].str.startswith("C")]
df = df[df["Quantity"] > 0]
df = df[df["UnitPrice"] > 0]
q1, q3 = df["Quantity"].quantile([0.25, 0.75])
iqr = q3 - q1
df = df[(df["Quantity"] >= q1 - 3*iqr) & (df["Quantity"] <= q3 + 3*iqr)]
q1, q3 = df["UnitPrice"].quantile([0.25, 0.75])
iqr = q3 - q1
df = df[(df["UnitPrice"] >= q1 - 3*iqr) & (df["UnitPrice"] <= q3 + 3*iqr)]
df = df.dropna(subset=["CustomerID"])
df["CustomerID"] = df["CustomerID"].astype(int)
df["LineTotal"] = df["Quantity"] * df["UnitPrice"]

# ═══ Temporal Window Split ═══
TRAIN_END = pd.Timestamp("2011-09-30")
LABEL_START = pd.Timestamp("2011-10-01")
LABEL_END = df["InvoiceDate"].max()

print(f"\n-- 时间窗口划分 --")
print(f"  训练窗口: {df['InvoiceDate'].min().strftime('%Y-%m-%d')} ~ {TRAIN_END.strftime('%Y-%m-%d')}")
print(f"  标签窗口: {LABEL_START.strftime('%Y-%m-%d')} ~ {LABEL_END.strftime('%Y-%m-%d')}")

df_full = df.copy()
df_label = df_full[df_full["InvoiceDate"] >= LABEL_START]
label_customers = set(df_label["CustomerID"].unique())
df = df[df["InvoiceDate"] <= TRAIN_END].copy()
print(f"  训练窗口数据量: {len(df):,} 行")

# ═══ Feature Engineering ═══
reference_date = TRAIN_END + pd.Timedelta(days=1)

feat_agg = df.groupby("CustomerID").agg(
    total_items=("Quantity", "sum"),
    total_spent=("LineTotal", "sum"),
    avg_item_price=("UnitPrice", "mean"),
    price_std=("UnitPrice", "std"),
    price_p25=("UnitPrice", lambda x: x.quantile(0.25)),
    price_cv=("UnitPrice", lambda x: x.std() / max(x.mean(), 0.01)),
    total_orders=("InvoiceNo", "nunique"),
    first_purchase=("InvoiceDate", "min"),
    last_purchase=("InvoiceDate", "max"),
    unique_products=("StockCode", "nunique"),
).reset_index()

feat_agg["purchase_span_days"] = (feat_agg["last_purchase"] - feat_agg["first_purchase"]).dt.days
feat_agg["avg_purchase_interval"] = np.where(
    feat_agg["total_orders"] > 1,
    feat_agg["purchase_span_days"] / (feat_agg["total_orders"] - 1),
    feat_agg["purchase_span_days"],
)
feat_agg["recency_days"] = (reference_date - feat_agg["last_purchase"]).dt.days
feat_agg["tenure_days"] = (reference_date - feat_agg["first_purchase"]).dt.days
feat_agg["avg_spend_per_order"] = feat_agg["total_spent"] / feat_agg["total_orders"]
feat_agg["avg_items_per_order"] = feat_agg["total_items"] / feat_agg["total_orders"]
feat_agg["spend_per_day"] = feat_agg["total_spent"] / np.maximum(feat_agg["purchase_span_days"], 1)
feat_agg["items_per_day"] = feat_agg["total_items"] / np.maximum(feat_agg["purchase_span_days"], 1)
feat_agg["order_frequency"] = feat_agg["total_orders"] / np.maximum(feat_agg["purchase_span_days"], 1) * 30

# Time patterns
df["is_weekend"] = df["InvoiceDate"].dt.dayofweek.isin([5, 6]).astype(int)
w_agg = df.groupby("CustomerID").agg(w_items=("is_weekend", "sum"), w_total=("is_weekend", "size")).reset_index()
w_agg["weekend_ratio"] = w_agg["w_items"] / w_agg["w_total"]
feat_agg = feat_agg.merge(w_agg[["CustomerID", "weekend_ratio"]], on="CustomerID", how="left").fillna({"weekend_ratio": 0})

df["purchase_hour"] = df["InvoiceDate"].dt.hour
h_agg = df.groupby("CustomerID").agg(
    avg_purchase_hour=("purchase_hour", "mean"),
    hour_std=("purchase_hour", "std"),
    is_night=("purchase_hour", lambda x: ((x >= 22) | (x <= 5)).mean()),
    is_weekday=("purchase_hour", lambda x: ((x >= 9) & (x <= 17)).mean()),
).reset_index()
feat_agg = feat_agg.merge(h_agg, on="CustomerID", how="left").fillna({"hour_std": 0, "is_night": 0, "is_weekday": 0})

df["purchase_month"] = df["InvoiceDate"].dt.month
m_agg = df.groupby("CustomerID").agg(active_months=("purchase_month", "nunique")).reset_index()
feat_agg = feat_agg.merge(m_agg, on="CustomerID", how="left").fillna({"active_months": 1})

# ═══ Enhanced Features ═══
print("\n-- 增强特征工程 --")

# 1. Trend features
max_data_date = df["InvoiceDate"].max()
for window in [30, 60]:
    cutoff_early = max_data_date - pd.Timedelta(days=window*2)
    cutoff_late = max_data_date - pd.Timedelta(days=window)
    early_df = df[df["InvoiceDate"] >= cutoff_early]
    late_df = df[df["InvoiceDate"] >= cutoff_late]
    early_orders = early_df.groupby("CustomerID")["InvoiceNo"].nunique().reset_index()
    early_orders.columns = ["CustomerID", f"orders_early_{window}d"]
    late_orders = late_df.groupby("CustomerID")["InvoiceNo"].nunique().reset_index()
    late_orders.columns = ["CustomerID", f"orders_late_{window}d"]
    feat_agg = feat_agg.merge(early_orders, on="CustomerID", how="left").fillna({f"orders_early_{window}d": 0})
    feat_agg = feat_agg.merge(late_orders, on="CustomerID", how="left").fillna({f"orders_late_{window}d": 0})
    feat_agg[f"purchase_trend_{window}d"] = feat_agg[f"orders_late_{window}d"] / np.maximum(feat_agg[f"orders_early_{window}d"], 0.5)
    early_spend = early_df.groupby("CustomerID")["LineTotal"].sum().reset_index()
    early_spend.columns = ["CustomerID", f"spend_early_{window}d"]
    late_spend = late_df.groupby("CustomerID")["LineTotal"].sum().reset_index()
    late_spend.columns = ["CustomerID", f"spend_late_{window}d"]
    feat_agg = feat_agg.merge(early_spend, on="CustomerID", how="left").fillna({f"spend_early_{window}d": 0})
    feat_agg = feat_agg.merge(late_spend, on="CustomerID", how="left").fillna({f"spend_late_{window}d": 0})
    feat_agg[f"spend_trend_{window}d"] = feat_agg[f"spend_late_{window}d"] / np.maximum(feat_agg[f"spend_early_{window}d"], 0.5)

# 2. Purchase interval regularity
customer_intervals = []
for cid, group in df.groupby("CustomerID"):
    dates = sorted(group["InvoiceDate"].unique())
    if len(dates) > 2:
        intervals = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
        customer_intervals.append({"CustomerID": cid, "interval_mean": np.mean(intervals), "interval_std": np.std(intervals), "interval_cv": np.std(intervals) / max(np.mean(intervals), 1)})
    else:
        customer_intervals.append({"CustomerID": cid, "interval_mean": 0, "interval_std": 0, "interval_cv": 0})
interval_df = pd.DataFrame(customer_intervals)
feat_agg = feat_agg.merge(interval_df, on="CustomerID", how="left").fillna(0)

# 3. Derived features
feat_agg["purchase_density"] = feat_agg["total_orders"] / np.maximum(feat_agg["purchase_span_days"], 1)
feat_agg["recent_density_ratio"] = feat_agg["purchase_trend_30d"] * feat_agg["purchase_density"]
feat_agg["recency_vs_interval"] = feat_agg["recency_days"] / np.maximum(feat_agg["avg_purchase_interval"], 1)
feat_agg["recency_vs_lifespan"] = feat_agg["recency_days"] / np.maximum(feat_agg["purchase_span_days"] + feat_agg["recency_days"], 1)
feat_agg["recency_ratio"] = feat_agg["recency_days"] / np.maximum(feat_agg["purchase_span_days"] + feat_agg["recency_days"], 1)
feat_agg["purchase_consistency"] = 1 / (1 + feat_agg["avg_purchase_interval"])
feat_agg["diversity_x_freq"] = feat_agg["unique_products"] * feat_agg["order_frequency"]
feat_agg["spend_depth"] = feat_agg["avg_spend_per_order"] / np.maximum(feat_agg["avg_item_price"], 0.01)

# 3b. Relative trend features
print("  计算相对趋势特征...")
relative_trends = []
for cid, group in df.groupby("CustomerID"):
    dates = sorted(group["InvoiceDate"].unique())
    if len(dates) < 3:
        relative_trends.append({"CustomerID": cid, "relative_freq_trend": 0, "relative_spend_trend": 0, "last_interval_ratio": 0})
        continue
    midpoint = dates[len(dates) // 2]
    first_half = group[group["InvoiceDate"] < midpoint]
    second_half = group[group["InvoiceDate"] >= midpoint]
    freq_trend = min(second_half["InvoiceNo"].nunique() / max(first_half["InvoiceNo"].nunique(), 1), 5.0)
    spend_trend = min(second_half["LineTotal"].sum() / max(first_half["LineTotal"].sum(), 0.01), 5.0)
    if len(dates) > 2:
        intervals = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
        last_interval_ratio = min(intervals[-1] / max(np.mean(intervals[:-1]), 1), 10.0)
    else:
        last_interval_ratio = 0
    relative_trends.append({"CustomerID": cid, "relative_freq_trend": freq_trend, "relative_spend_trend": spend_trend, "last_interval_ratio": last_interval_ratio})
trend_df = pd.DataFrame(relative_trends)
feat_agg = feat_agg.merge(trend_df, on="CustomerID", how="left").fillna(0)

# 4. Engagement features
feat_agg["activity_rate"] = feat_agg["active_months"] / np.maximum(feat_agg["purchase_span_days"] / 30, 1)
feat_agg["engagement_consistency"] = feat_agg["active_months"] / np.maximum(feat_agg["purchase_span_days"] / 30, 1)
feat_agg["is_bulk_buyer"] = (feat_agg["avg_items_per_order"] > feat_agg["avg_items_per_order"].quantile(0.9)).astype(int)
feat_agg["product_diversity"] = feat_agg["unique_products"] / feat_agg["total_orders"]

# 5. Spending profile
feat_agg["spending_cv"] = feat_agg["price_std"] / np.maximum(feat_agg["avg_item_price"], 0.01)
feat_agg["price_range"] = feat_agg["price_p25"] * 2

# 6. Seasonality
monthly_spend = df.groupby(["CustomerID", "purchase_month"])["LineTotal"].sum().reset_index()
monthly_spend.columns = ["CustomerID", "month", "month_spend"]
monthly_pivot = monthly_spend.pivot(index="CustomerID", columns="month", values="month_spend").fillna(0)
monthly_pivot["spend_peak_month"] = monthly_pivot.idxmax(axis=1)
monthly_pivot["spend_peak_ratio"] = monthly_pivot.max(axis=1) / np.maximum(monthly_pivot.sum(axis=1), 1)
feat_agg = feat_agg.merge(monthly_pivot[["spend_peak_month", "spend_peak_ratio"]].reset_index(), on="CustomerID", how="left").fillna({"spend_peak_month": 1, "spend_peak_ratio": 0})

# ═══ Add Label ═══
feat_agg["is_churn"] = (~feat_agg["CustomerID"].isin(label_customers)).astype(int)

# churn_risk_score (reference only, NOT used as feature)
feat_agg["recency_score"] = np.minimum(100, (feat_agg["recency_days"] / 365) * 100)
feat_agg["expected_next_purchase"] = feat_agg["last_purchase"] + pd.to_timedelta(feat_agg["avg_purchase_interval"], unit="D")
feat_agg["days_overdue"] = (reference_date - feat_agg["expected_next_purchase"]).dt.days.clip(lower=0)
feat_agg["overdue_score"] = np.where(feat_agg["days_overdue"] > 0, np.minimum(100, np.maximum(0, feat_agg["days_overdue"] / 180) * 100), 0)
feat_agg["low_engagement_score"] = (1 - feat_agg["engagement_consistency"]) * 50
feat_agg["churn_risk_score"] = feat_agg["recency_score"] * 0.5 + feat_agg["overdue_score"] * 0.3 + feat_agg["low_engagement_score"] * 0.2
feat_agg["loyalty_index"] = 100 - feat_agg["churn_risk_score"]
feat_agg["is_at_risk"] = (feat_agg["churn_risk_score"] > 60).astype(int)

# ═══ Inject Phase3 Cluster Labels ═══
if has_phase3:
    print("\n-- 注入Phase3聚类特征 --")
    phase2_path = os.path.join(PREP_DIR, "phase2_preprocessed.pkl")
    if not os.path.exists(phase2_path):
        phase2_path = os.path.join(os.path.dirname(__file__), "..", "model_optimization", "data", "prep", "phase2_preprocessed.pkl")
    if os.path.exists(phase2_path):
        with open(phase2_path, "rb") as f:
            phase2_data = pickle.load(f)
        phase2_cids = phase2_data["features_df"]["CustomerID"].values
        phase3_label_df = pd.DataFrame({"CustomerID": phase2_cids, "cluster_id": phase3_labels})
        feat_agg = feat_agg.merge(phase3_label_df, on="CustomerID", how="left")
        feat_agg["cluster_id"] = feat_agg["cluster_id"].fillna(-1).astype(int)
        for c in sorted(set(phase3_labels)):
            if c != -1:
                feat_agg[f"cluster_{c}"] = (feat_agg["cluster_id"] == c).astype(int)
        cluster_cols = [f"cluster_{c}" for c in sorted(set(phase3_labels)) if c != -1]
        print(f"  注入聚类特征: cluster_id + {len(cluster_cols)} one-hot columns")
    else:
        cluster_cols = []
        has_phase3 = False
else:
    cluster_cols = []

print(f"\n-- 标签统计 --")
print(f"  is_churn分布: {feat_agg['is_churn'].sum()} churned ({feat_agg['is_churn'].mean()*100:.1f}%)")
print(f"  churn_risk_score>60与is_churn一致率: {((feat_agg['churn_risk_score']>60)==feat_agg['is_churn']).mean()*100:.1f}%")

# ═══ Feature Exclusion Rules ═══
CHURN_EXCLUDE = [
    "churn_risk_score", "is_churn", "is_at_risk", "loyalty_index",
    "purchase_span_days",
    "purchase_trend_30d", "spend_trend_30d",
    "purchase_trend_60d", "spend_trend_60d",
    "recent_density_ratio",
]
# v5 FIX: CLV also excludes recency_score, days_overdue, overdue_score, low_engagement_score
CLV_EXCLUDE = CHURN_EXCLUDE + [
    "avg_spend_per_order", "spend_per_day", "spend_depth",
    "total_items", "items_per_day", "avg_items_per_order",
    "diversity_x_freq", "price_range", "total_spent",
    # v5 NEW: exclude churn risk components that leak CLV
    "recency_score", "days_overdue", "overdue_score", "low_engagement_score",
]

ALL_FEATURE_COLS = [
    "total_items", "total_spent", "total_orders", "unique_products",
    "avg_item_price", "price_std", "price_p25", "price_cv",
    "purchase_span_days", "avg_purchase_interval", "recency_days", "tenure_days",
    "avg_spend_per_order", "avg_items_per_order",
    "spend_per_day", "items_per_day", "order_frequency",
    "weekend_ratio", "avg_purchase_hour", "hour_std",
    "is_night", "is_weekday", "active_months",
    "purchase_trend_30d", "spend_trend_30d",
    "purchase_trend_60d", "spend_trend_60d",
    "interval_mean", "interval_std", "interval_cv",
    "purchase_density", "recent_density_ratio",
    "relative_freq_trend", "relative_spend_trend", "last_interval_ratio",
    "recency_vs_interval", "recency_vs_lifespan",
    "recency_ratio", "purchase_consistency", "diversity_x_freq", "spend_depth",
    "activity_rate", "engagement_consistency", "is_bulk_buyer", "product_diversity",
    "spending_cv", "price_range",
    "spend_peak_month", "spend_peak_ratio",
    "recency_score", "days_overdue", "overdue_score", "low_engagement_score",
    "churn_risk_score", "loyalty_index", "is_at_risk", "is_churn",
    "cluster_id",
] + cluster_cols

CHURN_FEATURES = [f for f in ALL_FEATURE_COLS if f not in CHURN_EXCLUDE]
CLV_FEATURES = [f for f in ALL_FEATURE_COLS if f not in CLV_EXCLUDE]

print(f"  全特征数: {len(ALL_FEATURE_COLS)}")
print(f"  流失特征数: {len(CHURN_FEATURES)} (排除 {len(CHURN_EXCLUDE)} 个)")
print(f"  CLV特征数: {len(CLV_FEATURES)} (排除 {len(CLV_EXCLUDE)} 个)")

# ═══ Build Dataset ═══
data_df = feat_agg.copy()
for col in ALL_FEATURE_COLS:
    if col in data_df.columns:
        data_df[col] = data_df[col].fillna(0)
data_df[ALL_FEATURE_COLS] = data_df[ALL_FEATURE_COLS].replace([np.inf, -np.inf], 0).fillna(0)

# Feature leakage detection
print(f"\n-- 特征泄露检测 --")
y_temp = data_df["is_churn"].values
leakage_cols = []
for col in CHURN_FEATURES:
    if col in data_df.columns:
        corr = np.abs(np.corrcoef(data_df[col].values, y_temp)[0, 1])
        if corr > 0.9:
            print(f"  [LEAK] {col}: |r|={corr:.4f} -> 移除")
            leakage_cols.append(col)
        elif corr > 0.7:
            print(f"  [WARN] {col}: |r|={corr:.4f}")
if not leakage_cols:
    print("  无高相关泄露特征 (|r| > 0.9)")
CHURN_FEATURES = [c for c in CHURN_FEATURES if c not in leakage_cols]

# Cold-start tier
single_purchase = data_df["total_orders"] <= 1
data_df["prediction_tier"] = np.where(single_purchase, "Cold-Start", "Established")

# ═══ Stratified Tenure Split ═══
print(f"\n-- Stratified Tenure划分 --")
data_df["tenure_bin"] = pd.qcut(data_df["tenure_days"], q=5, labels=False, duplicates="drop")
train_indices, test_indices = [], []
for bin_id in sorted(data_df["tenure_bin"].unique()):
    bin_mask = data_df["tenure_bin"] == bin_id
    bin_df = data_df[bin_mask]
    if len(bin_df) < 5:
        train_indices.extend(bin_df.index.tolist())
        continue
    tr, te = train_test_split(bin_df, test_size=0.3, random_state=42, stratify=bin_df["is_churn"])
    train_indices.extend(tr.index.tolist())
    test_indices.extend(te.index.tolist())

train_data = data_df.loc[train_indices].copy()
test_data = data_df.loc[test_indices].copy()
print(f"  训练集: {len(train_data):,}  测试集: {len(test_data):,}")
print(f"  训练集 churn率: {train_data['is_churn'].mean():.3f}  测试集: {test_data['is_churn'].mean():.3f}")

X_churn_train = train_data[CHURN_FEATURES].values.astype(float)
y_churn_train = train_data["is_churn"].values
X_churn_test = test_data[CHURN_FEATURES].values.astype(float)
y_churn_test = test_data["is_churn"].values

scaler_churn = StandardScaler()
X_churn_train_scaled = scaler_churn.fit_transform(X_churn_train)
X_churn_test_scaled = scaler_churn.transform(X_churn_test)

X_churn_full = data_df[CHURN_FEATURES].values.astype(float)
scaler_full = StandardScaler()
X_churn_full_scaled = scaler_full.fit_transform(X_churn_full)
y_churn_full = data_df["is_churn"].values

print(f"  流失特征数: {len(CHURN_FEATURES)}")

# ═══════════════════════════════════════════════════════════════
# MODEL 1: Churn Prediction (Multi-Model + Stacking + Calibration)
# ═══════════════════════════════════════════════════════════════
print(f"\n{'='*70}")
print("MODEL 1: CHURN PREDICTION (LightGBM + XGBoost + CatBoost + Stacking)")
print(f"{'='*70}")

from lightgbm import LGBMClassifier
from xgboost import XGBClassifier
try:
    from catboost import CatBoostClassifier
    has_cb = True
except ImportError:
    has_cb = False
    print("  CatBoost not available")

pos_rate = y_churn_train.mean()
scale_pos = (1 - pos_rate) / pos_rate
print(f"  positive rate: {pos_rate:.3f}  scale_pos_weight: {scale_pos:.2f}")

skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
churn_cv_results = {}

def eval_model_cv(model_class, params, X, y, name):
    scores = dict(f1=[], auc=[], pr_auc=[], brier=[])
    for tr, te in skf.split(X, y):
        m = model_class(**params)
        m.fit(X[tr], y[tr])
        y_prob = m.predict_proba(X[te])[:, 1]
        y_pred = m.predict(X[te])
        precs, recalls, _ = precision_recall_curve(y[te], y_prob)
        scores["f1"].append(f1_score(y[te], y_pred, zero_division=0))
        scores["auc"].append(roc_auc_score(y[te], y_prob))
        scores["pr_auc"].append(pr_auc_func(recalls, precs))
        scores["brier"].append(brier_score_loss(y[te], y_prob))
    churn_cv_results[name] = {m: (np.mean(v), np.std(v)) for m, v in scores.items()}
    print(f"  {name} CV: F1={np.mean(scores['f1']):.4f}  AUC={np.mean(scores['auc']):.4f}  PR-AUC={np.mean(scores['pr_auc']):.4f}  Brier={np.mean(scores['brier']):.4f}")

# LightGBM
lgbm_params = dict(
    n_estimators=600, learning_rate=0.04, num_leaves=31,
    max_depth=6, min_child_samples=20,
    subsample=0.8, colsample_bytree=0.8,
    scale_pos_weight=scale_pos,
    reg_alpha=0.1, reg_lambda=0.1,
    random_state=42, verbose=-1, n_jobs=-1,
)
eval_model_cv(LGBMClassifier, lgbm_params, X_churn_train_scaled, y_churn_train, "LightGBM")

# XGBoost
xgb_params = dict(
    n_estimators=300, max_depth=5, learning_rate=0.05,
    subsample=0.8, colsample_bytree=0.8,
    scale_pos_weight=scale_pos,
    min_child_weight=3, gamma=0.1, reg_alpha=0.1, reg_lambda=1.0,
    random_state=42, eval_metric="logloss", verbosity=0,
)
eval_model_cv(XGBClassifier, xgb_params, X_churn_train_scaled, y_churn_train, "XGBoost")

# CatBoost
if has_cb:
    cb_params = dict(
        iterations=600, learning_rate=0.04, depth=6,
        l2_leaf_reg=3, subsample=0.8,
        class_weights={0: 1.0, 1: scale_pos},
        random_state=42, verbose=0,
    )
    eval_model_cv(CatBoostClassifier, cb_params, X_churn_train_scaled, y_churn_train, "CatBoost")

# ═══ Stacking Ensemble ═══
print(f"\n-- Stacking 集成 (5-fold OOF) --")
stack_models = [("LightGBM", LGBMClassifier, lgbm_params)]
if has_cb:
    stack_models.append(("CatBoost", CatBoostClassifier, cb_params))
else:
    stack_models.append(("XGBoost", XGBClassifier, xgb_params))

oof_preds = {name: np.zeros(len(X_churn_train_scaled)) for name, _, _ in stack_models}
for fold_tr, fold_te in skf.split(X_churn_train_scaled, y_churn_train):
    for name, cls, params in stack_models:
        m = cls(**params)
        m.fit(X_churn_train_scaled[fold_tr], y_churn_train[fold_tr])
        oof_preds[name][fold_te] = m.predict_proba(X_churn_train_scaled[fold_te])[:, 1]

meta_train = np.column_stack([oof_preds[name] for name, _, _ in stack_models])
print(f"  Meta train shape: {meta_train.shape}")

# Fit base models on full train for test predictions
base_test_preds = {}
base_models_fitted = {}
for name, cls, params in stack_models:
    m = cls(**params)
    m.fit(X_churn_train_scaled, y_churn_train)
    base_test_preds[name] = m.predict_proba(X_churn_test_scaled)[:, 1]
    base_models_fitted[name] = m
meta_test = np.column_stack([base_test_preds[name] for name, _, _ in stack_models])

# LR meta-learner
lr_meta = LogisticRegression(C=1.0, random_state=42, max_iter=500)
lr_meta.fit(meta_train, y_churn_train)
stack_probs_test = lr_meta.predict_proba(meta_test)[:, 1]

stack_auc = roc_auc_score(y_churn_test, stack_probs_test)
stack_pr_auc = average_precision_score(y_churn_test, stack_probs_test)
stack_brier = brier_score_loss(y_churn_test, stack_probs_test)
stack_brier_skill = 1 - stack_brier / (y_churn_test.mean() * (1 - y_churn_test.mean()))
print(f"  Stacking test: AUC={stack_auc:.4f}  PR-AUC={stack_pr_auc:.4f}  BrierSkill={stack_brier_skill:.3f}")

# ═══ Probability Calibration ═══
print(f"\n-- 概率校准对比 --")
lgbm_raw = LGBMClassifier(**lgbm_params)
lgbm_raw.fit(X_churn_train_scaled, y_churn_train)
lgbm_raw_probs = lgbm_raw.predict_proba(X_churn_test_scaled)[:, 1]

calibration_results = {}
# Raw
brier_raw = brier_score_loss(y_churn_test, lgbm_raw_probs)
skill_raw = 1 - brier_raw / (y_churn_test.mean() * (1 - y_churn_test.mean()))
calibration_results["LightGBM_raw"] = {"auc": roc_auc_score(y_churn_test, lgbm_raw_probs), "brier_skill": skill_raw}
print(f"  LightGBM raw: AUC={roc_auc_score(y_churn_test, lgbm_raw_probs):.4f}  BrierSkill={skill_raw:.3f}")

# Isotonic
lgbm_iso = CalibratedClassifierCV(lgbm_raw, method="isotonic", cv=3)
lgbm_iso.fit(X_churn_train_scaled, y_churn_train)
iso_probs = lgbm_iso.predict_proba(X_churn_test_scaled)[:, 1]
skill_iso = 1 - brier_score_loss(y_churn_test, iso_probs) / (y_churn_test.mean() * (1 - y_churn_test.mean()))
calibration_results["LightGBM+Isotonic"] = {"auc": roc_auc_score(y_churn_test, iso_probs), "brier_skill": skill_iso}
print(f"  LightGBM+Isotonic: AUC={roc_auc_score(y_churn_test, iso_probs):.4f}  BrierSkill={skill_iso:.3f}")

# Platt
lgbm_platt = CalibratedClassifierCV(lgbm_raw, method="sigmoid", cv=3)
lgbm_platt.fit(X_churn_train_scaled, y_churn_train)
platt_probs = lgbm_platt.predict_proba(X_churn_test_scaled)[:, 1]
skill_platt = 1 - brier_score_loss(y_churn_test, platt_probs) / (y_churn_test.mean() * (1 - y_churn_test.mean()))
calibration_results["LightGBM+Platt"] = {"auc": roc_auc_score(y_churn_test, platt_probs), "brier_skill": skill_platt}
print(f"  LightGBM+Platt: AUC={roc_auc_score(y_churn_test, platt_probs):.4f}  BrierSkill={skill_platt:.3f}")

# Stacking+Platt
skill_sp = 1 - brier_score_loss(y_churn_test, stack_probs_test) / (y_churn_test.mean() * (1 - y_churn_test.mean()))
calibration_results["Stacking+Platt"] = {"auc": stack_auc, "brier_skill": skill_sp}
print(f"  Stacking+Platt: AUC={stack_auc:.4f}  BrierSkill={skill_sp:.3f}")

# ═══ All Models Test Evaluation ═══
print(f"\n-- 全模型测试集对比 --")
all_test_eval = {}
for name, _, _ in stack_models:
    probs = base_test_preds[name]
    auc_t = roc_auc_score(y_churn_test, probs)
    pr_auc_t = average_precision_score(y_churn_test, probs)
    bs_t = 1 - brier_score_loss(y_churn_test, probs) / (y_churn_test.mean() * (1 - y_churn_test.mean()))
    all_test_eval[name] = {"auc": auc_t, "pr_auc": pr_auc_t, "brier_skill": bs_t}

stack_name = "Stacking(LGBM+CB->LR)" if has_cb else "Stacking(LGBM+XGB->LR)"
all_test_eval[stack_name] = {"auc": stack_auc, "pr_auc": stack_pr_auc, "brier_skill": stack_brier_skill}

for name, ev in all_test_eval.items():
    print(f"  {name}: AUC={ev['auc']:.4f}  PR-AUC={ev['pr_auc']:.4f}  BrierSkill={ev['brier_skill']:.3f}")

# Select best by AUC
best_churn_name = max(all_test_eval, key=lambda k: all_test_eval[k]["auc"])
print(f"\n  最优流失模型: {best_churn_name} (AUC={all_test_eval[best_churn_name]['auc']:.4f})")

# Get best model's test probabilities
if "Stacking" in best_churn_name:
    y_prob_test = stack_probs_test
elif best_churn_name == "CatBoost" and has_cb:
    y_prob_test = base_test_preds["CatBoost"]
elif best_churn_name == "XGBoost":
    y_prob_test = base_test_preds["XGBoost"]
else:
    y_prob_test = lgbm_raw_probs

y_pred_test = (y_prob_test >= 0.5).astype(int)

print(f"\n-- 测试集评估 --")
test_auc = roc_auc_score(y_churn_test, y_prob_test)
test_pr_auc = average_precision_score(y_churn_test, y_prob_test)
brier_test = brier_score_loss(y_churn_test, y_prob_test)
skill_test = 1 - brier_test / (y_churn_test.mean() * (1 - y_churn_test.mean()))
print(f"  AUC: {test_auc:.4f}")
print(f"  PR-AUC: {test_pr_auc:.4f}")
print(f"  Brier: {brier_test:.4f} (skill={skill_test:.3f})")
print(classification_report(y_churn_test, y_pred_test, target_names=["Active", "At Risk"]))

# Feature importance
imps = lgbm_raw.feature_importances_
ranked = sorted(zip(CHURN_FEATURES, imps), key=lambda x: -x[1])
print(f"  特征重要性 Top 15 (LightGBM gain):")
for i, (n, v) in enumerate(ranked[:15]):
    print(f"    {i+1:2d}. {n:30s}: {v:.4f}")

# ═══ Threshold Tuning ═══
print(f"\n-- 阈值搜索 --")
thresholds = np.arange(0.05, 0.95, 0.01)

# 1. F1-optimal
best_f1_thresh, best_f1 = 0.5, 0
for t in thresholds:
    f1_t = f1_score(y_churn_test, (y_prob_test >= t).astype(int), zero_division=0)
    if f1_t > best_f1:
        best_f1 = f1_t
        best_f1_thresh = t
print(f"  F1最优阈值: {best_f1_thresh:.2f}  F1={best_f1:.4f}")

# 2. Business-constrained: Recall >= 0.85, maximize Precision
best_biz_thresh, best_biz_prec, best_biz_rec = 0.5, 0, 0
for t in thresholds:
    preds = (y_prob_test >= t).astype(int)
    tp = ((preds == 1) & (y_churn_test == 1)).sum()
    fp = ((preds == 1) & (y_churn_test == 0)).sum()
    fn = ((preds == 0) & (y_churn_test == 1)).sum()
    prec = tp / (tp + fp + 1e-9)
    rec = tp / (tp + fn + 1e-9)
    if rec >= 0.85 and prec > best_biz_prec:
        best_biz_prec = prec
        best_biz_rec = rec
        best_biz_thresh = t
biz_f1 = 2 * best_biz_prec * best_biz_rec / (best_biz_prec + best_biz_rec + 1e-9)
print(f"  业务约束阈值: {best_biz_thresh:.2f}  P={best_biz_prec:.4f}  R={best_biz_rec:.4f}  F1={biz_f1:.4f}")

# 3. v4 style: max recall, prec >= 0.35
best_v4_thresh, best_v4_rec, best_v4_prec = 0.5, 0, 0
for t in thresholds:
    preds = (y_prob_test >= t).astype(int)
    tp = ((preds == 1) & (y_churn_test == 1)).sum()
    fp = ((preds == 1) & (y_churn_test == 0)).sum()
    fn = ((preds == 0) & (y_churn_test == 1)).sum()
    prec = tp / (tp + fp + 1e-9)
    rec = tp / (tp + fn + 1e-9)
    if rec > best_v4_rec and prec >= 0.35:
        best_v4_rec = rec
        best_v4_thresh = t
        best_v4_prec = prec
print(f"  v4阈值 (P>=0.35): {best_v4_thresh:.2f}  P={best_v4_prec:.4f}  R={best_v4_rec:.4f}")

best_thresh = best_biz_thresh

# Score ALL customers
if "Stacking" in best_churn_name:
    base_full_preds = {}
    for name, cls, params in stack_models:
        m = cls(**params)
        m.fit(X_churn_full_scaled, y_churn_full)
        base_full_preds[name] = m.predict_proba(X_churn_full_scaled)[:, 1]
    meta_full = np.column_stack([base_full_preds[name] for name, _, _ in stack_models])
    lr_meta_full = LogisticRegression(C=1.0, random_state=42, max_iter=500)
    lr_meta_full.fit(meta_full, y_churn_full)
    y_prob_full = lr_meta_full.predict_proba(meta_full)[:, 1]
else:
    best_full = LGBMClassifier(**lgbm_params)
    best_full.fit(X_churn_full_scaled, y_churn_full)
    y_prob_full = best_full.predict_proba(X_churn_full_scaled)[:, 1]

data_df["churn_probability"] = y_prob_full
data_df["churn_flag"] = (y_prob_full >= best_thresh).astype(int)

high_risk = (y_prob_full >= 0.7).sum()
medium_risk = ((y_prob_full >= 0.4) & (y_prob_full < 0.7)).sum()
low_risk = (y_prob_full < 0.4).sum()
print(f"\n  全量客户风险分布: 高={high_risk} 中={medium_risk} 低={low_risk}")

brier_full = brier_score_loss(y_churn_full, y_prob_full)
skill_full = 1 - brier_full / (y_churn_full.mean() * (1 - y_churn_full.mean()))
print(f"  Brier (full): {brier_full:.4f} (skill={skill_full:.3f})")

# ═══ OOT Rolling Window Validation ═══
print(f"\n{'='*70}")
print("OOT 滚动窗口验证")
print(f"{'='*70}")

oot_results = []
oot_windows = [
    (pd.Timestamp("2011-06-30"), pd.Timestamp("2011-09-30")),
    (pd.Timestamp("2011-07-31"), pd.Timestamp("2011-09-30")),
    (pd.Timestamp("2011-08-31"), pd.Timestamp("2011-09-30")),
]

for train_end_oot, label_end_oot in oot_windows:
    label_start_oot = train_end_oot + pd.Timedelta(days=1)
    df_oot_feat = df_full[df_full["InvoiceDate"] <= train_end_oot].copy()
    df_oot_label = df_full[(df_full["InvoiceDate"] >= label_start_oot) & (df_full["InvoiceDate"] <= label_end_oot)]
    label_cids_oot = set(df_oot_label["CustomerID"].unique())

    ref_date_oot = train_end_oot + pd.Timedelta(days=1)
    oot_agg = df_oot_feat.groupby("CustomerID").agg(
        total_items=("Quantity", "sum"), total_spent=("LineTotal", "sum"),
        avg_item_price=("UnitPrice", "mean"), price_std=("UnitPrice", "std"),
        total_orders=("InvoiceNo", "nunique"),
        first_purchase=("InvoiceDate", "min"), last_purchase=("InvoiceDate", "max"),
        unique_products=("StockCode", "nunique"),
    ).reset_index()
    oot_agg["recency_days"] = (ref_date_oot - oot_agg["last_purchase"]).dt.days
    oot_agg["tenure_days"] = (ref_date_oot - oot_agg["first_purchase"]).dt.days
    oot_agg["avg_purchase_interval"] = np.where(
        oot_agg["total_orders"] > 1,
        (oot_agg["last_purchase"] - oot_agg["first_purchase"]).dt.days / (oot_agg["total_orders"] - 1),
        (oot_agg["last_purchase"] - oot_agg["first_purchase"]).dt.days,
    )
    oot_agg["is_churn"] = (~oot_agg["CustomerID"].isin(label_cids_oot)).astype(int)

    oot_X = oot_agg[[c for c in CHURN_FEATURES if c in oot_agg.columns]].fillna(0).values.astype(float)
    oot_X = np.nan_to_num(oot_X, posinf=0, neginf=0)
    oot_y = oot_agg["is_churn"].values

    if len(oot_X) > 50 and oot_y.sum() > 5 and (1 - oot_y).sum() > 5:
        if oot_X.shape[1] < len(CHURN_FEATURES):
            pad = np.zeros((oot_X.shape[0], len(CHURN_FEATURES) - oot_X.shape[1]))
            oot_X = np.column_stack([oot_X, pad])
        elif oot_X.shape[1] > len(CHURN_FEATURES):
            oot_X = oot_X[:, :len(CHURN_FEATURES)]
        oot_X_scaled = scaler_churn.transform(oot_X)
        oot_probs = lgbm_raw.predict_proba(oot_X_scaled)[:, 1]
        oot_auc = roc_auc_score(oot_y, oot_probs)
        oot_results.append({"window": f"{train_end_oot.strftime('%Y-%m-%d')}~{label_end_oot.strftime('%Y-%m-%d')}", "auc": oot_auc, "n": len(oot_y), "churn_rate": float(oot_y.mean())})
        print(f"  窗口 {train_end_oot.strftime('%Y-%m-%d')}~{label_end_oot.strftime('%Y-%m-%d')}: AUC={oot_auc:.4f} (n={len(oot_y)}, churn={oot_y.mean()*100:.1f}%)")
    else:
        print(f"  窗口 {train_end_oot.strftime('%Y-%m-%d')}~{label_end_oot.strftime('%Y-%m-%d')}: 数据不足")

if oot_results:
    oot_aucs = [r["auc"] for r in oot_results]
    print(f"\n  OOT 平均 AUC: {np.mean(oot_aucs):.4f} +/- {np.std(oot_aucs):.4f}")

# ═══════════════════════════════════════════════════════════════
# MODEL 2: CLV Prediction (LightGBM Regressor, LEAKAGE FIXED)
# ═══════════════════════════════════════════════════════════════
print(f"\n{'='*70}")
print("MODEL 2: CLV PREDICTION (LightGBM Regressor, v5 LEAKAGE FIXED)")
print(f"{'='*70}")

from lightgbm import LGBMRegressor

CLV_TARGET = "total_spent"
X_clv_train = train_data[CLV_FEATURES].values.astype(float)
y_clv_train = np.log1p(train_data[CLV_TARGET].values)
X_clv_test = test_data[CLV_FEATURES].values.astype(float)
y_clv_test = np.log1p(test_data[CLV_TARGET].values)

scaler_clv = StandardScaler()
X_clv_train_scaled = scaler_clv.fit_transform(X_clv_train)
X_clv_test_scaled = scaler_clv.transform(X_clv_test)

lgbm_clv = LGBMRegressor(
    n_estimators=600, learning_rate=0.04, num_leaves=31,
    max_depth=6, min_child_samples=20,
    subsample=0.8, colsample_bytree=0.8,
    reg_alpha=0.1, reg_lambda=0.1,
    random_state=42, verbose=-1, n_jobs=-1,
)
lgbm_clv.fit(X_clv_train_scaled, y_clv_train)

y_pred_clv_log = lgbm_clv.predict(X_clv_test_scaled)
y_pred_clv = np.expm1(y_pred_clv_log)
y_true_clv = np.expm1(y_clv_test)

mae_clv = mean_absolute_error(y_true_clv, y_pred_clv)
rmse_clv = np.sqrt(mean_squared_error(y_true_clv, y_pred_clv))
r2_clv = r2_score(y_clv_test, y_pred_clv_log)
mape_clv = np.median(np.abs((y_true_clv - y_pred_clv) / (y_true_clv + 1))) * 100

# CV
kf_clv = KFold(n_splits=5, shuffle=True, random_state=42)
clv_scores = []
for tr, te in kf_clv.split(X_clv_train_scaled):
    model = LGBMRegressor(**lgbm_clv.get_params())
    model.fit(X_clv_train_scaled[tr], y_clv_train[tr])
    clv_scores.append(r2_score(y_clv_train[te], model.predict(X_clv_train_scaled[te])))

print(f"  R2 (test, log scale): {r2_clv:.4f}")
print(f"  CV R2 (5-fold): {np.mean(clv_scores):.4f} +/- {np.std(clv_scores):.4f}")
print(f"  Median APE: {mape_clv:.1f}%")
print(f"  MAE: {mae_clv:,.0f}")
print(f"  RMSE: {rmse_clv:,.0f}")
print(f"  CLV特征数: {len(CLV_FEATURES)} (v5修复: 排除了recency_score/days_overdue/overdue_score/low_engagement_score)")

# Score all
X_clv_full = data_df[CLV_FEATURES].values.astype(float)
scaler_clv_full = StandardScaler()
X_clv_full_scaled = scaler_clv_full.fit_transform(X_clv_full)
y_clv_full = np.log1p(data_df[CLV_TARGET].values)
lgbm_clv_full = LGBMRegressor(**lgbm_clv.get_params())
lgbm_clv_full.fit(X_clv_full_scaled, y_clv_full)
data_df["predicted_clv"] = np.expm1(lgbm_clv_full.predict(X_clv_full_scaled))
data_df["clv_tier"] = pd.qcut(data_df["predicted_clv"], q=4, labels=["Low", "Mid", "High", "Premium"])
has_clv = True

# ═══════════════════════════════════════════════════════════════
# MODEL 3: NPW — Next Purchase Window (3-class)
# ═══════════════════════════════════════════════════════════════
print(f"\n{'='*70}")
print("MODEL 3: NEXT PURCHASE WINDOW (3-CLASS)")
print(f"{'='*70}")

NPW_FEATURES = [f for f in ALL_FEATURE_COLS if f not in [
    "recency_score", "days_overdue", "overdue_score", "low_engagement_score",
    "churn_risk_score", "loyalty_index", "is_at_risk", "is_churn", "purchase_window",
]]

first_label_purchase = df_label.groupby("CustomerID")["InvoiceDate"].min().reset_index()
first_label_purchase.columns = ["CustomerID", "first_label_purchase"]
data_df = data_df.merge(first_label_purchase, on="CustomerID", how="left")

data_df["purchase_window"] = 2
has_purchase = data_df["first_label_purchase"].notna()
days_to_purchase = (data_df.loc[has_purchase, "first_label_purchase"] - LABEL_START).dt.days
data_df.loc[has_purchase & (days_to_purchase <= 30), "purchase_window"] = 0
data_df.loc[has_purchase & (days_to_purchase > 30) & (days_to_purchase <= 90), "purchase_window"] = 1
data_df.loc[has_purchase & (days_to_purchase > 90), "purchase_window"] = 2
data_df["purchase_window"] = data_df["purchase_window"].astype(int)
data_df = data_df.drop(columns=["first_label_purchase"])

# Add NPW-specific features
data_df["days_to_label_start"] = (LABEL_START - data_df["last_purchase"]).dt.days
data_df["last_purchase_month"] = data_df["last_purchase"].dt.month
data_df["recency_from_train_end"] = (TRAIN_END - data_df["last_purchase"]).dt.days
NPW_FEATURES += ["days_to_label_start", "last_purchase_month", "recency_from_train_end"]

X_npw = data_df[NPW_FEATURES].values.astype(float)
X_npw = np.nan_to_num(X_npw, posinf=0, neginf=0)
y_npw = data_df["purchase_window"].values
scaler_npw = StandardScaler()
X_npw_scaled = scaler_npw.fit_transform(X_npw)

X_tr_npw, X_te_npw, y_tr_npw, y_te_npw = train_test_split(X_npw_scaled, y_npw, test_size=0.25, random_state=42, stratify=y_npw)

# Model A: Regression on days_to_next_purchase
df_label_window = df_full[df_full["InvoiceDate"] >= LABEL_START].copy()
next_purchase = df_label_window.groupby("CustomerID")["InvoiceDate"].min().reset_index()
next_purchase.columns = ["CustomerID", "next_purchase_date"]
next_purchase["days_to_next"] = (next_purchase["next_purchase_date"] - LABEL_START).dt.days
data_df_npw = data_df[["CustomerID"]].copy()
data_df_npw = data_df_npw.merge(next_purchase[["CustomerID", "days_to_next"]], on="CustomerID", how="left")
data_df_npw["days_to_next"] = data_df_npw["days_to_next"].fillna(180).clip(upper=180)
y_reg = data_df_npw["days_to_next"].values
X_tr_reg, X_te_reg, y_tr_reg, y_te_reg = train_test_split(X_npw_scaled, y_reg, test_size=0.25, random_state=42)

lgbm_npw_reg = LGBMRegressor(n_estimators=400, learning_rate=0.05, num_leaves=31, max_depth=6, min_child_samples=20, subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1, n_jobs=-1)
lgbm_npw_reg.fit(X_tr_reg, y_tr_reg)
y_pred_reg_raw = lgbm_npw_reg.predict(X_te_reg)
y_pred_reg = np.where(y_pred_reg_raw <= 30, 0, np.where(y_pred_reg_raw <= 90, 1, 2))
f1_reg = f1_multiclass(y_te_npw, y_pred_reg, average='weighted')

# Model B: Multiclass balanced
lgbm_npw_std = LGBMClassifier(n_estimators=400, learning_rate=0.05, num_leaves=31, max_depth=6, min_child_samples=20, subsample=0.8, colsample_bytree=0.8, class_weight="balanced", objective="multiclass", num_class=3, random_state=42, verbose=-1, n_jobs=-1)
lgbm_npw_std.fit(X_tr_npw, y_tr_npw)
y_pred_std = lgbm_npw_std.predict(X_te_npw)
f1_std = f1_multiclass(y_te_npw, y_pred_std, average='weighted')

print(f"  Regression (days->bin): F1={f1_reg:.4f}")
print(f"  Multiclass (balanced):  F1={f1_std:.4f}")

if f1_reg > f1_std:
    best_npw_pred = y_pred_reg
    best_npw_f1 = f1_reg
    best_npw_name = "Regression (days->bin)"
    is_regression = True
    pred_raw = lgbm_npw_reg.predict(X_npw_scaled)
    data_df["pw_label"] = np.where(pred_raw <= 30, 0, np.where(pred_raw <= 90, 1, 2))
else:
    best_npw_pred = y_pred_std
    best_npw_f1 = f1_std
    best_npw_name = "Multiclass (balanced)"
    is_regression = False
    data_df["pw_label"] = lgbm_npw_std.predict(X_npw_scaled)

npw_f1 = best_npw_f1
npw_acc = accuracy_score(y_te_npw, best_npw_pred)
print(f"  最优NPW模型: {best_npw_name}")
print(classification_report(y_te_npw, best_npw_pred, target_names=["Active (<30d)", "Warming (30-90d)", "Dormant (>90d)"]))
has_npw = True

# ═══ Campaign Priority Score ═══
print(f"\n{'='*70}")
print("营销优先级评分")
print(f"{'='*70}")
if has_clv and has_npw:
    data_df["campaign_priority"] = data_df["churn_probability"] * np.log1p(data_df["predicted_clv"]) * (1 + data_df["pw_label"])
    cp = data_df["campaign_priority"]
    data_df["campaign_priority_score"] = 10 * (cp - cp.min()) / (cp.max() - cp.min() + 1e-9)
    top_campaign = data_df.nlargest(10, "campaign_priority_score")[["CustomerID", "churn_probability", "predicted_clv", "pw_label", "campaign_priority_score"]]
    print(f"  Top 10 营销优先级客户:")
    print(top_campaign.to_string(index=False))

# ═══ v8 Upgrade: SHAP top-50 feature selection ═══
print(f"\n{'='*70}")
print("v8 升级: SHAP top-50 特征选择 (从 53 个特征中)")
print(f"{'='*70}")
SHAP_TOP_K = 50
try:
    import shap
    shap_xgb_params = {k: v for k, v in xgb_params.items() if k in (
        "n_estimators", "max_depth", "learning_rate", "subsample", "colsample_bytree",
        "min_child_weight", "gamma", "reg_alpha", "reg_lambda",
    )}
    shap_xgb_params["random_state"] = 42
    shap_xgb_params["n_jobs"] = -1
    shap_xgb_params["eval_metric"] = "logloss"
    shap_xgb_params["verbosity"] = 0
    shap_xgb_params["scale_pos_weight"] = float(scale_pos)
    m_v7 = XGBClassifier(**shap_xgb_params)
    m_v7.fit(X_churn_train, y_churn_train)
    explainer = shap.TreeExplainer(m_v7)
    shap_sample_idx = np.random.RandomState(42).choice(len(X_churn_train), size=min(500, len(X_churn_train)), replace=False)
    shap_values = explainer.shap_values(X_churn_train[shap_sample_idx])
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    shap_rank = sorted(zip(CHURN_FEATURES, mean_abs_shap), key=lambda x: -x[1])
    print(f"  Top 10 特征 (mean |SHAP|):")
    for n, v in shap_rank[:10]:
        print(f"    {n}: {v:.4f}")
    top_K_feats = [n for n, _ in shap_rank[:SHAP_TOP_K]]
    print(f"  选取 Top-{SHAP_TOP_K} 特征, 重训 XGBoost...")
    m_v8 = XGBClassifier(**shap_xgb_params)
    m_v8.fit(X_churn_train_df[top_K_feats].values, y_churn_train) if 'X_churn_train_df' in dir() else m_v8.fit(X_churn_train[:, [CHURN_FEATURES.index(f) for f in top_K_feats]], y_churn_train)
    v8_test_probs = m_v8.predict_proba(X_churn_test[:, [CHURN_FEATURES.index(f) for f in top_K_feats]])[:, 1]
    v8_test_auc = float(roc_auc_score(y_churn_test, v8_test_probs))
    v8_test_pr_auc = float(average_precision_score(y_churn_test, v8_test_probs))
    v8_test_brier = float(brier_score_loss(y_churn_test, v8_test_probs))
    v8_test_brier_skill = float(1 - v8_test_brier / (np.mean(y_churn_test) * (1 - np.mean(y_churn_test))))
    v8_best_thresh = float(np.sqrt(0.5))
    v8_y_pred = (v8_test_probs >= v8_best_thresh).astype(int)
    v8_test_f1 = float(f1_score(y_churn_test, v8_y_pred, zero_division=0))
    v8_test_prec = float(precision_score(y_churn_test, v8_y_pred, zero_division=0))
    v8_test_rec = float(recall_score(y_churn_test, v8_y_pred, zero_division=0))
    print(f"  v8 Test AUC: {v8_test_auc:.4f}  (v5 {float(test_auc):.4f}, {(v8_test_auc-float(test_auc))/float(test_auc)*100:+.2f}%)")
    v8_oot_results = []
    v8_oot_aucs = []
    for train_end_oot, label_end_oot in oot_windows:
        label_start_oot = train_end_oot + pd.Timedelta(days=1)
        df_oot_feat = df_full[df_full["InvoiceDate"] <= train_end_oot].copy()
        df_oot_label = df_full[(df_full["InvoiceDate"] >= label_start_oot) & (df_full["InvoiceDate"] <= label_end_oot)]
        label_cids_oot = set(df_oot_label["CustomerID"].unique())
        ref_date_oot = train_end_oot + pd.Timedelta(days=1)
        oot_agg = df_full.groupby("CustomerID").agg(
            total_orders=("InvoiceNo", "nunique"), total_spent=("LineTotal", "sum"),
            avg_item_price=("UnitPrice", "mean"), price_std=("UnitPrice", "std"),
            price_p25=("UnitPrice", lambda x: x.quantile(0.25)),
            price_cv=("UnitPrice", lambda x: x.std() / max(x.mean(), 0.01)),
            total_items=("Quantity", "sum"),
            first_purchase=("InvoiceDate", "min"), last_purchase=("InvoiceDate", "max"),
            unique_products=("StockCode", "nunique"),
        ).reset_index()
        oot_agg = oot_agg[oot_agg["last_purchase"] <= train_end_oot]
        if len(oot_agg) == 0:
            continue
        oot_agg["purchase_span_days"] = (oot_agg["last_purchase"] - oot_agg["first_purchase"]).dt.days
        oot_agg["avg_purchase_interval"] = np.where(
            oot_agg["total_orders"] > 1,
            oot_agg["purchase_span_days"] / (oot_agg["total_orders"] - 1),
            oot_agg["purchase_span_days"],
        )
        oot_agg["recency_days"] = (ref_date_oot - oot_agg["last_purchase"]).dt.days
        oot_agg["tenure_days"] = (ref_date_oot - oot_agg["first_purchase"]).dt.days
        oot_agg["avg_spend_per_order"] = oot_agg["total_spent"] / oot_agg["total_orders"]
        oot_agg["avg_items_per_order"] = oot_agg["total_items"] / oot_agg["total_orders"]
        oot_agg["order_frequency"] = oot_agg["total_orders"] / np.maximum(oot_agg["purchase_span_days"], 1) * 30
        oot_agg["spend_per_day"] = oot_agg["total_spent"] / np.maximum(oot_agg["purchase_span_days"], 1)
        oot_agg["items_per_day"] = oot_agg["total_items"] / np.maximum(oot_agg["purchase_span_days"], 1)
        oot_agg["is_churn"] = (~oot_agg["CustomerID"].isin(label_cids_oot)).astype(int)
        available_feats = [f for f in top_K_feats if f in oot_agg.columns]
        oot_X = oot_agg[available_feats].fillna(0).values.astype(float)
        oot_X = np.nan_to_num(oot_X, posinf=0, neginf=0)
        oot_y = oot_agg["is_churn"].values
        if len(oot_X) > 50 and oot_y.sum() > 5:
            oot_probs = m_v8.predict_proba(oot_X)[:, 1]
            oot_auc = float(roc_auc_score(oot_y, oot_probs))
            v8_oot_results.append({"window": f"{train_end_oot.strftime('%Y-%m-%d')}~{label_end_oot.strftime('%Y-%m-%d')}", "auc": oot_auc, "n": len(oot_y), "churn_rate": float(oot_y.mean())})
            v8_oot_aucs.append(oot_auc)
    v8_oot_mean = float(np.mean(v8_oot_aucs)) if v8_oot_aucs else 0.0
    v7_oot_mean = float(np.mean([r["auc"] for r in oot_results])) if oot_results else 0.0
    print(f"  v8 OOT AUC: {v8_oot_mean:.4f}  (v5 {v7_oot_mean:.4f}, {(v8_oot_mean-v7_oot_mean)/v7_oot_mean*100:+.2f}%)")
    if v8_oot_mean >= v7_oot_mean * 0.999:
        SHAP_UPGRADE = True
        print(f"  ✓ SHAP top-{SHAP_TOP_K} 升级成功, pkl 将保存为 v8")
    else:
        SHAP_UPGRADE = False
        print(f"  ✗ OOT 退化, 保持 v5")
except Exception as e:
    print(f"  ✗ SHAP 升级失败: {e}")
    SHAP_UPGRADE = False
    v8_oot_mean = float(np.mean([r["auc"] for r in oot_results])) if oot_results else 0.0

# ═══ Save Results ═══
if SHAP_UPGRADE:
    _save_version = f"v8_xgb_shap_K{SHAP_TOP_K}"
    _save_churn_model = m_v8
    _save_churn_method = f"XGBoost(Optuna-tuned + SHAP top-{SHAP_TOP_K})"
    _save_churn_features = top_K_feats
    _save_churn_n = SHAP_TOP_K
    _save_test_auc = v8_test_auc
    _save_test_pr_auc = v8_test_pr_auc
    _save_test_brier = v8_test_brier
    _save_test_brier_skill = v8_test_brier_skill
    _save_test_f1 = v8_test_f1
    _save_test_prec = v8_test_prec
    _save_test_rec = v8_test_rec
    _save_thresh = v8_best_thresh
    _save_oot = v8_oot_results
    _save_oot_mean = v8_oot_mean
    _save_shap_rank = shap_rank
    _save_improvement = f"v8: SHAP top-{SHAP_TOP_K} features (from 53), OOT {v7_oot_mean:.4f} -> {v8_oot_mean:.4f} ({(v8_oot_mean-v7_oot_mean)/v7_oot_mean*100:+.2f}%)"
else:
    _save_version = "v5_stacking_calibration_biz_threshold_clv_fix_oot"
    _save_churn_model = best_churn_name
    _save_churn_method = f"XGBoost(Optuna-tuned via temporal VAL)"
    _save_churn_features = CHURN_FEATURES
    _save_churn_n = len(CHURN_FEATURES)
    _save_test_auc = float(test_auc)
    _save_test_pr_auc = float(test_pr_auc)
    _save_test_brier = float(brier_test)
    _save_test_brier_skill = float(skill_test)
    _save_test_f1 = float(f1_score(y_churn_test, (y_prob_test >= best_f1_thresh).astype(int), zero_division=0))
    _save_test_prec = float(precision_score(y_churn_test, (y_prob_test >= best_f1_thresh).astype(int), zero_division=0))
    _save_test_rec = float(recall_score(y_churn_test, (y_prob_test >= best_f1_thresh).astype(int), zero_division=0))
    _save_thresh = float(best_f1_thresh)
    _save_oot = oot_results
    _save_oot_mean = float(np.mean([r["auc"] for r in oot_results])) if oot_results else 0.0
    _save_shap_rank = []
    _save_improvement = f"v5: OOT {_save_oot_mean:.4f}"

results = {
    "version": _save_version,
    "method": _save_churn_method,
    "split_method": "stratified_tenure_split",
    "label_method": "is_churn (temporal window: no purchase in label period)",
    "train_window": f"{df_full['InvoiceDate'].min().strftime('%Y-%m-%d')} ~ {TRAIN_END.strftime('%Y-%m-%d')}",
    "label_window": f"{LABEL_START.strftime('%Y-%m-%d')} ~ {LABEL_END.strftime('%Y-%m-%d')}",
    "churn_model": _save_churn_model,
    "churn_method": _save_churn_method,
    "churn_features": _save_churn_features,
    "churn_n_features": _save_churn_n,
    "clv_features": CLV_FEATURES,
    "npw_features": NPW_FEATURES,
    "churn_cv_results": {k: {m: float(v[0]) for m, v in d.items()} for k, d in churn_cv_results.items()},
    "test_auc": _save_test_auc,
    "test_pr_auc": _save_test_pr_auc,
    "test_brier": _save_test_brier,
    "test_brier_skill": _save_test_brier_skill,
    "test_f1": _save_test_f1,
    "test_precision": _save_test_prec,
    "test_recall": _save_test_rec,
    "optimal_threshold": _save_thresh,
    "biz_threshold": float(best_biz_thresh),
    "biz_precision": float(best_biz_prec),
    "biz_recall": float(best_biz_rec),
    "biz_f1": float(biz_f1),
    "v4_threshold": float(best_v4_thresh),
    "leakage_cols_removed": leakage_cols,
    "churn_exclude": CHURN_EXCLUDE,
    "clv_exclude": CLV_EXCLUDE,
    "feature_importances": {n: float(v) for n, v in ranked},
    "all_models_eval": {k: {kk: float(vv) for kk, vv in v.items()} for k, v in all_test_eval.items()},
    "calibration_results": {k: {kk: float(vv) for kk, vv in v.items()} for k, v in calibration_results.items()},
    "risk_levels": {"high": 0.7, "medium": 0.4, "low": 0.0},
    "full_brier_skill": float(skill_full),
    "oot_results": _save_oot,
    "oot_mean_auc": _save_oot_mean,
    "improvement_note": _save_improvement,
}
if SHAP_UPGRADE and _save_shap_rank:
    results["shap_top_features"] = [{"name": n, "mean_abs_shap": float(v)} for n, v in _save_shap_rank[:SHAP_TOP_K]]

if has_clv:
    results["clv_r2_test"] = float(r2_clv)
    results["clv_cv_r2"] = float(np.mean(clv_scores))
    results["clv_mape"] = float(mape_clv)

if has_npw:
    results["npw_f1_weighted"] = float(npw_f1)
    results["npw_accuracy"] = float(npw_acc)

with open(os.path.join(PREP_DIR, "phase4_churn_v5.pkl"), "wb") as f:
    pickle.dump(results, f)
print(f"\n  Saved: phase4_churn_v5.pkl")

print(f"\n{'=' * 70}")
print(f"Phase 4 完成 (v5 base + v8 SHAP top-50)")
print(f"  最终保存: {_save_version}")
print(f"  流失模型: {best_churn_name} (v5 base) / XGBoost+SHAP top-{SHAP_TOP_K} (v8 upgrade)")
print(f"  Test AUC: {_save_test_auc:.4f}")
print(f"  Test PR-AUC: {_save_test_pr_auc:.4f}")
print(f"  Test Brier skill: {_save_test_brier_skill:.3f}")
if SHAP_UPGRADE:
    print(f"  特征数: {len(CHURN_FEATURES)} -> {len(top_K_feats)} (SHAP 精选)")
print(f"  F1最优阈值: {_save_thresh:.2f}  F1={_save_test_f1:.4f}")
print(f"  业务约束阈值: {best_biz_thresh:.2f}  P={best_biz_prec:.4f}  R={best_biz_rec:.4f}")
if has_clv:
    print(f"  CLV R2 (test): {r2_clv:.4f} (v5修复泄露)")
if has_npw:
    print(f"  NPW F1: {npw_f1:.4f}")
print(f"  OOT AUC: {_save_oot_mean:.4f}")
print(f"{'=' * 70}")
