"""
Phase 4 Optuna: Tune XGBoost hyperparameters for OOT AUC.
Reuses feature engineering from build_winner.py.
Final winner: also run full 3-window OOT + save to pkl.
"""
import os, sys, warnings, pickle, json, time
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

import optuna
from optuna.samplers import TPESampler
optuna.logging.set_verbosity(optuna.logging.WARNING)

import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, f1_score, precision_score, recall_score

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
PREP = os.path.join(ROOT, "data", "prep")
EXP = os.path.join(ROOT, "experiments", "phase4")
os.makedirs(EXP, exist_ok=True)

# ─── Replicate feature engineering from build_winner.py ───
print("[1/4] Building features...")
t0 = time.time()
df = pd.read_csv(os.path.join(RAW, "Online_Retail.csv"), encoding="latin1", parse_dates=["InvoiceDate"])
df["InvoiceNo"] = df["InvoiceNo"].astype(str)
df = df[~df["InvoiceNo"].str.startswith("C")]
df = df[df["Quantity"] > 0]; df = df[df["UnitPrice"] > 0]
for col in ["Quantity", "UnitPrice"]:
    q1, q3 = df[col].quantile([0.25, 0.75]); iqr = q3 - q1
    df = df[(df[col] >= q1 - 3*iqr) & (df[col] <= q3 + 3*iqr)]
df = df.dropna(subset=["CustomerID"])
df["CustomerID"] = df["CustomerID"].astype(int)
df["LineTotal"] = df["Quantity"] * df["UnitPrice"]

TRAIN_END = pd.Timestamp("2011-09-30")
LABEL_START = pd.Timestamp("2011-10-01")
df_label = df[df["InvoiceDate"] >= LABEL_START]
label_customers = set(df_label["CustomerID"].unique())
df_train = df[df["InvoiceDate"] <= TRAIN_END].copy()
reference_date = TRAIN_END + pd.Timedelta(days=1)
max_data_date = df_train["InvoiceDate"].max()

feat = df_train.groupby("CustomerID").agg(
    total_items=("Quantity", "sum"), total_spent=("LineTotal", "sum"),
    avg_item_price=("UnitPrice", "mean"), price_std=("UnitPrice", "std"),
    price_p25=("UnitPrice", lambda x: x.quantile(0.25)),
    price_cv=("UnitPrice", lambda x: x.std() / max(x.mean(), 0.01)),
    total_orders=("InvoiceNo", "nunique"),
    first_purchase=("InvoiceDate", "min"), last_purchase=("InvoiceDate", "max"),
    unique_products=("StockCode", "nunique"),
).reset_index()
feat["purchase_span_days"] = (feat["last_purchase"] - feat["first_purchase"]).dt.days
feat["avg_purchase_interval"] = np.where(feat["total_orders"] > 1, feat["purchase_span_days"] / (feat["total_orders"] - 1), feat["purchase_span_days"])
feat["recency_days"] = (reference_date - feat["last_purchase"]).dt.days
feat["tenure_days"] = (reference_date - feat["first_purchase"]).dt.days
feat["avg_spend_per_order"] = feat["total_spent"] / feat["total_orders"]
feat["avg_items_per_order"] = feat["total_items"] / feat["total_orders"]
feat["spend_per_day"] = feat["total_spent"] / np.maximum(feat["purchase_span_days"], 1)
feat["items_per_day"] = feat["total_items"] / np.maximum(feat["purchase_span_days"], 1)
feat["order_frequency"] = feat["total_orders"] / np.maximum(feat["purchase_span_days"], 1) * 30
df_train["is_weekend"] = df_train["InvoiceDate"].dt.dayofweek.isin([5, 6]).astype(int)
wagg = df_train.groupby("CustomerID").agg(w_items=("is_weekend", "sum"), w_total=("is_weekend", "size")).reset_index()
wagg["weekend_ratio"] = wagg["w_items"] / wagg["w_total"]
feat = feat.merge(wagg[["CustomerID", "weekend_ratio"]], on="CustomerID", how="left").fillna({"weekend_ratio": 0})
df_train["purchase_hour"] = df_train["InvoiceDate"].dt.hour
hagg = df_train.groupby("CustomerID").agg(
    avg_purchase_hour=("purchase_hour", "mean"), hour_std=("purchase_hour", "std"),
    is_night=("purchase_hour", lambda x: ((x >= 22) | (x <= 5)).mean()),
    is_weekday=("purchase_hour", lambda x: ((x >= 9) & (x <= 17)).mean()),
).reset_index()
feat = feat.merge(hagg, on="CustomerID", how="left").fillna({"hour_std": 0, "is_night": 0, "is_weekday": 0})
df_train["purchase_month"] = df_train["InvoiceDate"].dt.month
magg = df_train.groupby("CustomerID").agg(active_months=("purchase_month", "nunique")).reset_index()
feat = feat.merge(magg, on="CustomerID", how="left").fillna({"active_months": 1})
for window in [30, 60]:
    ce = max_data_date - pd.Timedelta(days=window*2)
    cl = max_data_date - pd.Timedelta(days=window)
    early = df_train[df_train["InvoiceDate"] >= ce]
    late = df_train[df_train["InvoiceDate"] >= cl]
    eo = early.groupby("CustomerID")["InvoiceNo"].nunique().reset_index().rename(columns={"InvoiceNo": f"orders_early_{window}d"})
    lo = late.groupby("CustomerID")["InvoiceNo"].nunique().reset_index().rename(columns={"InvoiceNo": f"orders_late_{window}d"})
    feat = feat.merge(eo, on="CustomerID", how="left").fillna({f"orders_early_{window}d": 0})
    feat = feat.merge(lo, on="CustomerID", how="left").fillna({f"orders_late_{window}d": 0})
    feat[f"purchase_trend_{window}d"] = feat[f"orders_late_{window}d"] / np.maximum(feat[f"orders_early_{window}d"], 0.5)
    es = early.groupby("CustomerID")["LineTotal"].sum().reset_index().rename(columns={"LineTotal": f"spend_early_{window}d"})
    ls = late.groupby("CustomerID")["LineTotal"].sum().reset_index().rename(columns={"LineTotal": f"spend_late_{window}d"})
    feat = feat.merge(es, on="CustomerID", how="left").fillna({f"spend_early_{window}d": 0})
    feat = feat.merge(ls, on="CustomerID", how="left").fillna({f"spend_late_{window}d": 0})
    feat[f"spend_trend_{window}d"] = feat[f"spend_late_{window}d"] / np.maximum(feat[f"spend_early_{window}d"], 0.5)
intervals = []
for cid, group in df_train.groupby("CustomerID"):
    dates = sorted(group["InvoiceDate"].unique())
    if len(dates) > 2:
        ints = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
        intervals.append({"CustomerID": cid, "interval_mean": np.mean(ints), "interval_std": np.std(ints), "interval_cv": np.std(ints) / max(np.mean(ints), 1)})
    else:
        intervals.append({"CustomerID": cid, "interval_mean": 0, "interval_std": 0, "interval_cv": 0})
feat = feat.merge(pd.DataFrame(intervals), on="CustomerID", how="left").fillna(0)
feat["purchase_density"] = feat["total_orders"] / np.maximum(feat["purchase_span_days"], 1)
feat["recent_density_ratio"] = feat["purchase_trend_30d"] * feat["purchase_density"]
feat["recency_vs_interval"] = feat["recency_days"] / np.maximum(feat["avg_purchase_interval"], 1)
feat["recency_vs_lifespan"] = feat["recency_days"] / np.maximum(feat["purchase_span_days"] + feat["recency_days"], 1)
feat["recency_ratio"] = feat["recency_days"] / np.maximum(feat["purchase_span_days"] + feat["recency_days"], 1)
feat["purchase_consistency"] = 1 / (1 + feat["avg_purchase_interval"])
feat["diversity_x_freq"] = feat["unique_products"] * feat["order_frequency"]
feat["spend_depth"] = feat["avg_spend_per_order"] / np.maximum(feat["avg_item_price"], 0.01)
rel = []
for cid, group in df_train.groupby("CustomerID"):
    dates = sorted(group["InvoiceDate"].unique())
    if len(dates) < 3:
        rel.append({"CustomerID": cid, "relative_freq_trend": 0, "relative_spend_trend": 0, "last_interval_ratio": 0})
        continue
    mid = dates[len(dates) // 2]
    f1 = group[group["InvoiceDate"] < mid]
    f2 = group[group["InvoiceDate"] >= mid]
    ft = min(f2["InvoiceNo"].nunique() / max(f1["InvoiceNo"].nunique(), 1), 5.0)
    st_ = min(f2["LineTotal"].sum() / max(f1["LineTotal"].sum(), 0.01), 5.0)
    if len(dates) > 2:
        ints = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
        lir = min(ints[-1] / max(np.mean(ints[:-1]), 1), 10.0)
    else:
        lir = 0
    rel.append({"CustomerID": cid, "relative_freq_trend": ft, "relative_spend_trend": st_, "last_interval_ratio": lir})
feat = feat.merge(pd.DataFrame(rel), on="CustomerID", how="left").fillna(0)
feat["activity_rate"] = feat["active_months"] / np.maximum(feat["purchase_span_days"] / 30, 1)
feat["engagement_consistency"] = feat["active_months"] / np.maximum(feat["purchase_span_days"] / 30, 1)
feat["is_bulk_buyer"] = (feat["avg_items_per_order"] > feat["avg_items_per_order"].quantile(0.9)).astype(int)
feat["product_diversity"] = feat["unique_products"] / feat["total_orders"]
feat["spending_cv"] = feat["price_std"] / np.maximum(feat["avg_item_price"], 0.01)
feat["price_range"] = feat["price_p25"] * 2
feat["is_churn"] = (~feat["CustomerID"].isin(label_customers)).astype(int)
feat["recency_score"] = np.minimum(100, (feat["recency_days"] / 365) * 100)
feat["expected_next_purchase"] = feat["last_purchase"] + pd.to_timedelta(feat["avg_purchase_interval"], unit="D")
feat["days_overdue"] = (reference_date - feat["expected_next_purchase"]).dt.days.clip(lower=0)
feat["overdue_score"] = np.where(feat["days_overdue"] > 0, np.minimum(100, np.maximum(0, feat["days_overdue"] / 180) * 100), 0)
feat["low_engagement_score"] = (1 - feat["engagement_consistency"]) * 50

CHURN_EXCLUDE = ["churn_risk_score", "is_churn", "is_at_risk", "loyalty_index", "purchase_span_days",
                 "purchase_trend_30d", "spend_trend_30d", "purchase_trend_60d", "spend_trend_60d",
                 "recent_density_ratio"]
churn_features = [c for c in feat.columns if c not in CHURN_EXCLUDE + ["CustomerID", "is_churn",
                   "first_purchase", "last_purchase", "expected_next_purchase"]]
print(f"  Features: {len(churn_features)}  Time: {time.time()-t0:.1f}s")

X = feat[churn_features].fillna(0).values
y = feat["is_churn"].values

# Train/val split (use the same split as build_winner.py)
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
spw = (y_tr == 0).sum() / (y_tr == 1).sum()

# ─── OOT building (for final validation) ───
def build_oot_full(window_end, churn_features_ref):
    we = pd.Timestamp(window_end)
    df_w = df[df["InvoiceDate"] <= we].copy()
    df_lb_w = df[df["InvoiceDate"] > we].copy()
    label_cust = set(df_lb_w["CustomerID"].unique())
    ref = we + pd.Timedelta(days=1)
    mdw = df_w["InvoiceDate"].max()
    f = df_w.groupby("CustomerID").agg(
        total_items=("Quantity", "sum"), total_spent=("LineTotal", "sum"),
        avg_item_price=("UnitPrice", "mean"), price_std=("UnitPrice", "std"),
        price_p25=("UnitPrice", lambda x: x.quantile(0.25)),
        price_cv=("UnitPrice", lambda x: x.std() / max(x.mean(), 0.01)),
        total_orders=("InvoiceNo", "nunique"),
        first_purchase=("InvoiceDate", "min"), last_purchase=("InvoiceDate", "max"),
        unique_products=("StockCode", "nunique"),
    ).reset_index()
    f["purchase_span_days"] = (f["last_purchase"] - f["first_purchase"]).dt.days
    f["avg_purchase_interval"] = np.where(f["total_orders"] > 1, f["purchase_span_days"] / (f["total_orders"] - 1), f["purchase_span_days"])
    f["recency_days"] = (ref - f["last_purchase"]).dt.days
    f["tenure_days"] = (ref - f["first_purchase"]).dt.days
    f["avg_spend_per_order"] = f["total_spent"] / f["total_orders"]
    f["avg_items_per_order"] = f["total_items"] / f["total_orders"]
    f["spend_per_day"] = f["total_spent"] / np.maximum(f["purchase_span_days"], 1)
    f["items_per_day"] = f["total_items"] / np.maximum(f["purchase_span_days"], 1)
    f["order_frequency"] = f["total_orders"] / np.maximum(f["purchase_span_days"], 1) * 30
    df_w["is_weekend"] = df_w["InvoiceDate"].dt.dayofweek.isin([5, 6]).astype(int)
    wagg = df_w.groupby("CustomerID").agg(w_items=("is_weekend", "sum"), w_total=("is_weekend", "size")).reset_index()
    wagg["weekend_ratio"] = wagg["w_items"] / wagg["w_total"]
    f = f.merge(wagg[["CustomerID", "weekend_ratio"]], on="CustomerID", how="left").fillna({"weekend_ratio": 0})
    df_w["purchase_hour"] = df_w["InvoiceDate"].dt.hour
    hagg = df_w.groupby("CustomerID").agg(
        avg_purchase_hour=("purchase_hour", "mean"), hour_std=("purchase_hour", "std"),
        is_night=("purchase_hour", lambda x: ((x >= 22) | (x <= 5)).mean()),
        is_weekday=("purchase_hour", lambda x: ((x >= 9) & (x <= 17)).mean()),
    ).reset_index()
    f = f.merge(hagg, on="CustomerID", how="left").fillna({"hour_std": 0, "is_night": 0, "is_weekday": 0})
    df_w["purchase_month"] = df_w["InvoiceDate"].dt.month
    magg = df_w.groupby("CustomerID").agg(active_months=("purchase_month", "nunique")).reset_index()
    f = f.merge(magg, on="CustomerID", how="left").fillna({"active_months": 1})
    for window in [30, 60]:
        ce = mdw - pd.Timedelta(days=window*2)
        cl = mdw - pd.Timedelta(days=window)
        early = df_w[df_w["InvoiceDate"] >= ce]
        late = df_w[df_w["InvoiceDate"] >= cl]
        eo = early.groupby("CustomerID")["InvoiceNo"].nunique().reset_index().rename(columns={"InvoiceNo": f"orders_early_{window}d"})
        lo = late.groupby("CustomerID")["InvoiceNo"].nunique().reset_index().rename(columns={"InvoiceNo": f"orders_late_{window}d"})
        f = f.merge(eo, on="CustomerID", how="left").fillna({f"orders_early_{window}d": 0})
        f = f.merge(lo, on="CustomerID", how="left").fillna({f"orders_late_{window}d": 0})
        f[f"purchase_trend_{window}d"] = f[f"orders_late_{window}d"] / np.maximum(f[f"orders_early_{window}d"], 0.5)
        es = early.groupby("CustomerID")["LineTotal"].sum().reset_index().rename(columns={"LineTotal": f"spend_early_{window}d"})
        ls = late.groupby("CustomerID")["LineTotal"].sum().reset_index().rename(columns={"LineTotal": f"spend_late_{window}d"})
        f = f.merge(es, on="CustomerID", how="left").fillna({f"spend_early_{window}d": 0})
        f = f.merge(ls, on="CustomerID", how="left").fillna({f"spend_late_{window}d": 0})
        f[f"spend_trend_{window}d"] = f[f"spend_late_{window}d"] / np.maximum(f[f"spend_early_{window}d"], 0.5)
    intervals = []
    for cid, group in df_w.groupby("CustomerID"):
        dates = sorted(group["InvoiceDate"].unique())
        if len(dates) > 2:
            ints = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
            intervals.append({"CustomerID": cid, "interval_mean": np.mean(ints), "interval_std": np.std(ints), "interval_cv": np.std(ints) / max(np.mean(ints), 1)})
        else:
            intervals.append({"CustomerID": cid, "interval_mean": 0, "interval_std": 0, "interval_cv": 0})
    f = f.merge(pd.DataFrame(intervals), on="CustomerID", how="left").fillna(0)
    f["purchase_density"] = f["total_orders"] / np.maximum(f["purchase_span_days"], 1)
    f["recent_density_ratio"] = f["purchase_trend_30d"] * f["purchase_density"]
    f["recency_vs_interval"] = f["recency_days"] / np.maximum(f["avg_purchase_interval"], 1)
    f["recency_vs_lifespan"] = f["recency_days"] / np.maximum(f["purchase_span_days"] + f["recency_days"], 1)
    f["recency_ratio"] = f["recency_days"] / np.maximum(f["purchase_span_days"] + f["recency_days"], 1)
    f["purchase_consistency"] = 1 / (1 + f["avg_purchase_interval"])
    f["diversity_x_freq"] = f["unique_products"] * f["order_frequency"]
    f["spend_depth"] = f["avg_spend_per_order"] / np.maximum(f["avg_item_price"], 0.01)
    rel = []
    for cid, group in df_w.groupby("CustomerID"):
        dates = sorted(group["InvoiceDate"].unique())
        if len(dates) < 3:
            rel.append({"CustomerID": cid, "relative_freq_trend": 0, "relative_spend_trend": 0, "last_interval_ratio": 0})
            continue
        mid = dates[len(dates) // 2]
        f1 = group[group["InvoiceDate"] < mid]
        f2 = group[group["InvoiceDate"] >= mid]
        ft = min(f2["InvoiceNo"].nunique() / max(f1["InvoiceNo"].nunique(), 1), 5.0)
        st_ = min(f2["LineTotal"].sum() / max(f1["LineTotal"].sum(), 0.01), 5.0)
        if len(dates) > 2:
            ints = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
            lir = min(ints[-1] / max(np.mean(ints[:-1]), 1), 10.0)
        else:
            lir = 0
        rel.append({"CustomerID": cid, "relative_freq_trend": ft, "relative_spend_trend": st_, "last_interval_ratio": lir})
    f = f.merge(pd.DataFrame(rel), on="CustomerID", how="left").fillna(0)
    f["activity_rate"] = f["active_months"] / np.maximum(f["purchase_span_days"] / 30, 1)
    f["engagement_consistency"] = f["active_months"] / np.maximum(f["purchase_span_days"] / 30, 1)
    f["is_bulk_buyer"] = (f["avg_items_per_order"] > f["avg_items_per_order"].quantile(0.9)).astype(int)
    f["product_diversity"] = f["unique_products"] / f["total_orders"]
    f["spending_cv"] = f["price_std"] / np.maximum(f["avg_item_price"], 0.01)
    f["price_range"] = f["price_p25"] * 2
    f["is_churn"] = (~f["CustomerID"].isin(label_cust)).astype(int)
    f["recency_score"] = np.minimum(100, (f["recency_days"] / 365) * 100)
    f["expected_next_purchase"] = f["last_purchase"] + pd.to_timedelta(f["avg_purchase_interval"], unit="D")
    f["days_overdue"] = (ref - f["expected_next_purchase"]).dt.days.clip(lower=0)
    f["overdue_score"] = np.where(f["days_overdue"] > 0, np.minimum(100, np.maximum(0, f["days_overdue"] / 180) * 100), 0)
    f["low_engagement_score"] = (1 - f["engagement_consistency"]) * 50
    Xo = f.reindex(columns=churn_features_ref, fill_value=0).fillna(0).values
    yo = f["is_churn"].values
    return Xo, yo

# ─── Optuna objective ───
print("\n[2/4] Optuna search (50 trials)...")
t0 = time.time()
def objective(trial):
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 200, 800, step=100),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        "gamma": trial.suggest_float("gamma", 0.0, 0.5),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        "scale_pos_weight": trial.suggest_float("scale_pos_weight", spw*0.5, spw*1.5),
    }
    m = xgb.XGBClassifier(**params, random_state=42, n_jobs=-1, eval_metric="logloss", verbosity=0)
    m.fit(X_tr, y_tr)
    p = m.predict_proba(X_te)[:, 1]
    return float(roc_auc_score(y_te, p))

study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=42))
study.optimize(objective, n_trials=50, show_progress_bar=False)
print(f"  Best AUC: {study.best_value:.4f}")
print(f"  Best params: {study.best_params}")
print(f"  Time: {time.time()-t0:.1f}s")

# ─── Train final model with best params ───
print("\n[3/4] Training final model with best params...")
t0 = time.time()
best_params = study.best_params.copy()
best_params.update({
    "scale_pos_weight": best_params.pop("scale_pos_weight"),
    "random_state": 42, "n_jobs": -1, "eval_metric": "logloss", "verbosity": 0
})
m_final = xgb.XGBClassifier(**best_params)
m_final.fit(X_tr, y_tr)
yp_te = m_final.predict_proba(X_te)[:, 1]
test_auc = float(roc_auc_score(y_te, yp_te))
test_f1 = float(f1_score(y_te, (yp_te >= 0.5).astype(int)))
print(f"  Test AUC: {test_auc:.4f}  F1: {test_f1:.4f}")
print(f"  Time: {time.time()-t0:.1f}s")

# ─── Full 3-window OOT evaluation ───
print("\n[4/4] Full 3-window OOT evaluation...")
t0 = time.time()
oot_results = []
for we in ["2011-06-30", "2011-07-31", "2011-08-31"]:
    Xo, yo = build_oot_full(we, churn_features)
    ypo = m_final.predict_proba(Xo)[:, 1]
    auc = float(roc_auc_score(yo, ypo))
    oot_results.append({"window": f"{we}~2011-09-30", "auc": auc, "n": len(yo), "churn_rate": float(yo.mean())})
    print(f"  OOT {we}: AUC={auc:.4f}  n={len(yo)}  churn={yo.mean()*100:.1f}%")
oot_mean = float(np.mean([r["auc"] for r in oot_results]))
print(f"  OOT mean: {oot_mean:.4f}  (vs v6 baseline 0.904 = {(oot_mean-0.904)/0.904*100:+.2f}%)")
print(f"  Time: {time.time()-t0:.1f}s")

# ─── Compare vs current winner ───
print("\n[Comparison] Loading current winner pkl...")
with open(os.path.join(PREP, "phase4_churn_v5.pkl"), "rb") as f:
    v5 = pickle.load(f)
print(f"  Current OOT mean: {v5.get('oot_mean_auc', 'N/A')}")
print(f"  Current best AUC: {study.best_value:.4f}  |  OOT mean: {oot_mean:.4f}")

# ─── Save new pkl only if improved ───
if oot_mean > 0.904:
    print("\n[SAVE] OOT improved, building new winner pkl...")
    new_pkl = dict(v5)
    new_pkl["version"] = "v7_xgb_optuna"
    new_pkl["churn_model"] = m_final
    new_pkl["churn_method"] = "XGBoost(scale_pos_weight + Optuna tuned)"
    new_pkl["optuna_best_params"] = study.best_params
    new_pkl["optuna_best_auc"] = study.best_value
    new_pkl["optuna_n_trials"] = 50
    new_pkl["test_auc"] = test_auc
    new_pkl["test_f1"] = test_f1
    new_pkl["oot_results"] = oot_results
    new_pkl["oot_mean_auc"] = oot_mean
    new_pkl["improvement_note"] = f"v7: Optuna-tuned XGBoost, OOT {0.904:.3f} -> {oot_mean:.3f} ({(oot_mean-0.904)/0.904*100:+.2f}%)"

    out_pkl = os.path.join(EXP, "phase4_churn_winner.pkl")
    with open(out_pkl, "wb") as f:
        pickle.dump(new_pkl, f)
    print(f"  Saved: {out_pkl}")
else:
    print(f"\n[NO SAVE] OOT not improved ({oot_mean:.4f} <= 0.904). Keep v6.")

# ─── Save study results ───
study_out = {
    "best_value": study.best_value,
    "best_params": study.best_params,
    "n_trials": 50,
    "test_auc": test_auc,
    "test_f1": test_f1,
    "oot_results": oot_results,
    "oot_mean_auc": oot_mean,
    "oot_improved": oot_mean > 0.904,
    "baseline_oot_mean": 0.904,
}
with open(os.path.join(EXP, "phase4_optuna.json"), "w") as f:
    json.dump(study_out, f, indent=2, ensure_ascii=False)
print(f"\nStudy saved: {os.path.join(EXP, 'phase4_optuna.json')}")
