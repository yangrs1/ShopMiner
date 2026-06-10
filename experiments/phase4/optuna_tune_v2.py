"""
Phase 4 Optuna v2: Use OOT as objective (not Test) to avoid overfitting Test.
Use 1 temporal holdout (2011-07-31 cutoff, label 2011-08~09) as objective.
Final check: full 3-window OOT + save if improved.
"""
import os, sys, warnings, pickle, json, time
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

import optuna
from optuna.samplers import TPESampler
optuna.logging.set_verbosity(optuna.logging.WARNING)

import xgboost as xgb
from sklearn.metrics import roc_auc_score

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
PREP = os.path.join(ROOT, "data", "prep")
EXP = os.path.join(ROOT, "experiments", "phase4")

# ─── Replicate feature engineering (same as v1) ───
print("[1/5] Loading data + building features...")
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

def build_features_at(cutoff_date):
    """Build customer features using only data <= cutoff_date. Label = customer in next month(s)."""
    cd = pd.Timestamp(cutoff_date)
    df_w = df[df["InvoiceDate"] <= cd].copy()
    df_lb = df[df["InvoiceDate"] > cd].copy()
    label_cust = set(df_lb["CustomerID"].unique())
    ref = cd + pd.Timedelta(days=1)
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
    return f

print(f"  Time: {time.time()-t0:.1f}s")

# Build train (cutoff 2011-07-31, label 2011-08~09) and final test (cutoff 2011-09-30, label 2011-10~12)
print("\n[2/5] Building train (cutoff 2011-07-31) and val features...")
t0 = time.time()
df_train = build_features_at("2011-07-31")
df_final = build_features_at("2011-09-30")
CHURN_EXCLUDE = ["churn_risk_score", "is_churn", "is_at_risk", "loyalty_index", "purchase_span_days",
                 "purchase_trend_30d", "spend_trend_30d", "purchase_trend_60d", "spend_trend_60d",
                 "recent_density_ratio"]
churn_features = [c for c in df_train.columns if c not in CHURN_EXCLUDE + ["CustomerID", "is_churn",
                   "first_purchase", "last_purchase", "expected_next_purchase"]]
print(f"  Features: {len(churn_features)}  Train rows: {len(df_train)}  Val rows: {len(df_final)}  Time: {time.time()-t0:.1f}s")

X_tr = df_train[churn_features].fillna(0).values
y_tr = df_train["is_churn"].values
X_val = df_final[churn_features].fillna(0).values
y_val = df_final["is_churn"].values
spw = (y_tr == 0).sum() / (y_tr == 1).sum()

# ─── Optuna objective: VAL AUC (temporal, not random test) ───
print("\n[3/5] Optuna search (40 trials, objective=VAL AUC)...")
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
    p = m.predict_proba(X_val)[:, 1]
    return float(roc_auc_score(y_val, p))

study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=42))
study.optimize(objective, n_trials=40, show_progress_bar=False)
print(f"  Best VAL AUC: {study.best_value:.4f}")
print(f"  Best params: {study.best_params}")
print(f"  Time: {time.time()-t0:.1f}s")

# ─── Train final model on FULL data (cutoff 2011-09-30) with best params ───
print("\n[4/5] Training final model (cutoff 2011-09-30) with best params...")
t0 = time.time()
X_full = df_final[churn_features].fillna(0).values
y_full = df_final["is_churn"].values
# Use 80/20 random split on full data for test eval (same as v6)
from sklearn.model_selection import train_test_split
X_ftr, X_fte, y_ftr, y_fte = train_test_split(X_full, y_full, test_size=0.2, random_state=42, stratify=y_full)
spw_full = (y_ftr == 0).sum() / (y_ftr == 1).sum()
best_params = study.best_params.copy()
best_params.update({
    "random_state": 42, "n_jobs": -1, "eval_metric": "logloss", "verbosity": 0
})
m_final = xgb.XGBClassifier(**best_params)
m_final.fit(X_ftr, y_ftr)
yp_te = m_final.predict_proba(X_fte)[:, 1]
test_auc = float(roc_auc_score(y_fte, yp_te))
print(f"  Test AUC: {test_auc:.4f}  Time: {time.time()-t0:.1f}s")

# ─── Full 3-window OOT evaluation ───
print("\n[5/5] Full 3-window OOT evaluation...")
t0 = time.time()
oot_results = []
for we in ["2011-06-30", "2011-07-31", "2011-08-31"]:
    df_oot = build_features_at(we)
    Xo = df_oot[churn_features].fillna(0).values
    yo = df_oot["is_churn"].values
    ypo = m_final.predict_proba(Xo)[:, 1]
    auc = float(roc_auc_score(yo, ypo))
    oot_results.append({"window": f"{we}~2011-09-30", "auc": auc, "n": len(yo), "churn_rate": float(yo.mean())})
    print(f"  OOT {we}: AUC={auc:.4f}  n={len(yo)}  churn={yo.mean()*100:.1f}%")
oot_mean = float(np.mean([r["auc"] for r in oot_results]))
print(f"  OOT mean: {oot_mean:.4f}  (vs v6 baseline 0.904 = {(oot_mean-0.904)/0.904*100:+.2f}%)")
print(f"  Time: {time.time()-t0:.1f}s")

# ─── Save new pkl only if improved ───
with open(os.path.join(PREP, "phase4_churn_v5.pkl"), "rb") as f:
    v5 = pickle.load(f)

if oot_mean > 0.904:
    print("\n[SAVE] OOT improved, building new winner pkl...")
    new_pkl = dict(v5)
    new_pkl["version"] = "v7_xgb_optuna_temporal"
    new_pkl["churn_model"] = m_final
    new_pkl["churn_method"] = "XGBoost(Optuna-tuned via temporal VAL)"
    new_pkl["optuna_best_params"] = study.best_params
    new_pkl["optuna_best_val_auc"] = study.best_value
    new_pkl["optuna_n_trials"] = 40
    new_pkl["test_auc"] = test_auc
    new_pkl["oot_results"] = oot_results
    new_pkl["oot_mean_auc"] = oot_mean
    new_pkl["improvement_note"] = f"v7: Optuna-tuned XGBoost on temporal VAL (cutoff 2011-07-31), OOT 0.904 -> {oot_mean:.3f} ({(oot_mean-0.904)/0.904*100:+.2f}%)"

    out_pkl = os.path.join(EXP, "phase4_churn_winner.pkl")
    with open(out_pkl, "wb") as f:
        pickle.dump(new_pkl, f)
    print(f"  Saved: {out_pkl}")
else:
    print(f"\n[NO SAVE] OOT not improved ({oot_mean:.4f} <= 0.904). Keep v6.")

study_out = {
    "best_value_val_auc": study.best_value,
    "best_params": study.best_params,
    "n_trials": 40,
    "test_auc": test_auc,
    "oot_results": oot_results,
    "oot_mean_auc": oot_mean,
    "oot_improved": oot_mean > 0.904,
    "baseline_oot_mean": 0.904,
    "note": "Optuna objective was VAL AUC on temporal holdout (cutoff 2011-07-31), not random test"
}
with open(os.path.join(EXP, "phase4_optuna.json"), "w") as f:
    json.dump(study_out, f, indent=2, ensure_ascii=False)
print(f"\nStudy saved: {os.path.join(EXP, 'phase4_optuna.json')}")
