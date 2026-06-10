"""
Phase 4 SHAP: Feature selection via SHAP importance.
1. Train v7 XGBoost on all features
2. Compute SHAP values (TreeExplainer) on full data
3. Iteratively try top-K features (K=20, 30, 40, 50) and re-evaluate OOT
4. Save best K features + new pkl if OOT improved
"""
import os, sys, warnings, pickle, json, time
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

import shap
import xgboost as xgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
PREP = os.path.join(ROOT, "data", "prep")
EXP = os.path.join(ROOT, "experiments", "phase4")

# ─── Replicate feature engineering (same as v7) ───
print("[1/5] Building features...")
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
print("\n[2/5] Building full data (cutoff 2011-09-30)...")
t0 = time.time()
df_full = build_features_at("2011-09-30")
CHURN_EXCLUDE = ["churn_risk_score", "is_churn", "is_at_risk", "loyalty_index", "purchase_span_days",
                 "purchase_trend_30d", "spend_trend_30d", "purchase_trend_60d", "spend_trend_60d",
                 "recent_density_ratio"]
churn_features = [c for c in df_full.columns if c not in CHURN_EXCLUDE + ["CustomerID", "is_churn",
                   "first_purchase", "last_purchase", "expected_next_purchase"]]
X = df_full[churn_features].fillna(0).values
y = df_full["is_churn"].values
print(f"  Features: {len(churn_features)}  Rows: {len(X)}  Time: {time.time()-t0:.1f}s")

X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
spw = (y_tr == 0).sum() / (y_tr == 1).sum()

# ─── Train v7 model on full train, compute SHAP ───
print("\n[3/5] Training v7 model and computing SHAP values...")
t0 = time.time()
with open(os.path.join(EXP, "phase4_optuna.json"), "r") as f:
    optuna_best = json.load(f)
v7_params = optuna_best["best_params"]
v7_params.update({"random_state": 42, "n_jobs": -1, "eval_metric": "logloss", "verbosity": 0})
m_v7 = xgb.XGBClassifier(**v7_params)
m_v7.fit(X_tr, y_tr)
yp = m_v7.predict_proba(X_te)[:, 1]
v7_test_auc = float(roc_auc_score(y_te, yp))
print(f"  v7 Test AUC: {v7_test_auc:.4f}")

# SHAP on a sample of 500 (TreeExplainer on full train is fast, but values array is large)
explainer = shap.TreeExplainer(m_v7)
shap_sample_idx = np.random.RandomState(42).choice(len(X_tr), size=min(500, len(X_tr)), replace=False)
shap_values = explainer.shap_values(X_tr[shap_sample_idx])
mean_abs_shap = np.abs(shap_values).mean(axis=0)
shap_rank = sorted(zip(churn_features, mean_abs_shap), key=lambda x: -x[1])
print(f"  Top 10 features by mean |SHAP|:")
for name, val in shap_rank[:10]:
    print(f"    {name}: {val:.4f}")
print(f"  Time: {time.time()-t0:.1f}s")

# ─── Try top-K features and re-evaluate OOT ───
print("\n[4/5] Iterative K search (K=20, 30, 40, 50)...")
t0 = time.time()
def oot_eval(features_subset, params, m_class):
    aucs = []
    for we in ["2011-06-30", "2011-07-31", "2011-08-31"]:
        df_oot = build_features_at(we)
        Xo = df_oot[features_subset].fillna(0).values
        yo = df_oot["is_churn"].values
        ypo = m_class.predict_proba(Xo)[:, 1]
        aucs.append(float(roc_auc_score(yo, ypo)))
    return float(np.mean(aucs)), aucs

results = {}
for K in [20, 30, 40, 50]:
    top_K_feats = [name for name, _ in shap_rank[:K]]
    X_tr_sub = df_full[top_K_feats].fillna(0).iloc[X_tr.shape[0]:].values if False else df_full[top_K_feats].fillna(0).values
    # Re-split with same indices
    Xtr_K = X_tr_sub[:len(X_tr)]  # not quite right, let's use indices
    from sklearn.model_selection import train_test_split
    Xtr_K, Xte_K, ytr_K, yte_K = train_test_split(X_tr_sub, y, test_size=0.2, random_state=42, stratify=y)
    spw_K = (ytr_K == 0).sum() / (ytr_K == 1).sum()
    p = v7_params.copy()
    p["scale_pos_weight"] = spw_K
    m = xgb.XGBClassifier(**p)
    m.fit(Xtr_K, ytr_K)
    yp_te = m.predict_proba(Xte_K)[:, 1]
    test_auc_K = float(roc_auc_score(yte_K, yp_te))
    oot_mean_K, oot_each_K = oot_eval(top_K_feats, v7_params, m)
    results[K] = {"test_auc": test_auc_K, "oot_mean": oot_mean_K, "oot_each": oot_each_K, "n_features": K, "features": top_K_feats}
    print(f"  K={K}: Test={test_auc_K:.4f}  OOT mean={oot_mean_K:.4f}  OOT each={[round(x,3) for x in oot_each_K]}")
print(f"  Time: {time.time()-t0:.1f}s")

# Load v7 (current best) for baseline comparison
with open(os.path.join(PREP, "phase4_churn_v5.pkl"), "rb") as f:
    v7_pkl = pickle.load(f)
v7_oot_mean = v7_pkl.get("oot_mean_auc", 0.913)
print(f"\n  v7 baseline OOT: {v7_oot_mean:.4f}")

# ─── Save best K ───
print("\n[5/5] Selecting best K and saving...")
best_K = max(results, key=lambda k: results[k]["oot_mean"])
best = results[best_K]
print(f"  Best K: {best_K}  OOT mean: {best['oot_mean']:.4f}  (vs v7 {v7_oot_mean:.4f}, {(best['oot_mean']-v7_oot_mean)/v7_oot_mean*100:+.2f}%)")

if best["oot_mean"] > v7_oot_mean:
    # Re-train final with best K + best Optuna params
    top_K_feats = best["features"]
    X_sub = df_full[top_K_feats].fillna(0).values
    Xtr_K, Xte_K, ytr_K, yte_K = train_test_split(X_sub, y, test_size=0.2, random_state=42, stratify=y)
    spw_K = (ytr_K == 0).sum() / (ytr_K == 1).sum()
    p = v7_params.copy()
    p["scale_pos_weight"] = spw_K
    m_final = xgb.XGBClassifier(**p)
    m_final.fit(Xtr_K, ytr_K)
    yp_te = m_final.predict_proba(Xte_K)[:, 1]
    test_auc = float(roc_auc_score(yte_K, yp_te))
    oot_mean, oot_each = oot_eval(top_K_feats, p, m_final)

    print(f"\n[SAVE] SHAP-selected {best_K} features: OOT {v7_oot_mean:.4f} -> {oot_mean:.4f} ({(oot_mean-v7_oot_mean)/v7_oot_mean*100:+.2f}%)")
    new_pkl = dict(v7_pkl)
    new_pkl["version"] = f"v8_xgb_shap_K{best_K}"
    new_pkl["churn_model"] = m_final
    new_pkl["churn_method"] = f"XGBoost(Optuna-tuned + SHAP top-{best_K})"
    new_pkl["churn_features"] = top_K_feats
    new_pkl["churn_n_features"] = best_K
    new_pkl["shap_top_features"] = [{"name": n, "mean_abs_shap": float(v)} for n, v in shap_rank[:best_K]]
    new_pkl["test_auc"] = test_auc
    new_pkl["oot_results"] = [{"window": f"{we}~2011-09-30", "auc": a} for we, a in zip(["2011-06-30", "2011-07-31", "2011-08-31"], oot_each)]
    new_pkl["oot_mean_auc"] = oot_mean
    new_pkl["improvement_note"] = f"v8: SHAP top-{best_K} features (from 53), OOT {v7_oot_mean:.4f} -> {oot_mean:.4f} ({(oot_mean-v7_oot_mean)/v7_oot_mean*100:+.2f}%)"

    out_pkl = os.path.join(EXP, "phase4_churn_winner.pkl")
    with open(out_pkl, "wb") as f:
        pickle.dump(new_pkl, f)
    print(f"  Saved: {out_pkl}")
else:
    print(f"\n[NO SAVE] OOT not improved. Keep v7.")

# Save SHAP analysis
shap_out = {
    "shap_top50": [{"name": n, "mean_abs_shap": float(v)} for n, v in shap_rank[:50]],
    "iter_results": {str(k): {"test_auc": v["test_auc"], "oot_mean": v["oot_mean"], "oot_each": v["oot_each"], "n_features": v["n_features"]} for k, v in results.items()},
    "best_K": best_K,
    "v7_baseline_oot": v7_oot_mean,
    "improved": bool(best["oot_mean"] > v7_oot_mean),
}
with open(os.path.join(EXP, "phase4_shap.json"), "w") as f:
    json.dump(shap_out, f, indent=2, ensure_ascii=False, default=str)
print(f"\nStudy saved: {os.path.join(EXP, 'phase4_shap.json')}")
