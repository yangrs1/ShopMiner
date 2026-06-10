"""
生成 4 个模型的图表数据，写入 data/prep/phase*_viz.json
由 compute_analytics.py 在重算时调用
"""
import os, sys, json, pickle, time
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PREP = os.path.join(ROOT, "data", "prep")
RAW = os.path.join(ROOT, "data", "raw")


def load_pkl(name):
    with open(os.path.join(PREP, name), "rb") as f:
        return pickle.load(f)


def load_raw():
    df = pd.read_csv(os.path.join(RAW, "Online_Retail.csv"), encoding="latin1", parse_dates=["InvoiceDate"])
    df["InvoiceNo"] = df["InvoiceNo"].astype(str)
    df = df[~df["InvoiceNo"].str.startswith("C")]
    df = df[df["Quantity"] > 0]
    df = df[df["UnitPrice"] > 0]
    for col in ["Quantity", "UnitPrice"]:
        q1, q3 = df[col].quantile([0.25, 0.75])
        iqr = q3 - q1
        df = df[(df[col] >= q1 - 3*iqr) & (df[col] <= q3 + 3*iqr)]
    df = df.dropna(subset=["CustomerID"])
    df["CustomerID"] = df["CustomerID"].astype(int)
    df["LineTotal"] = df["Quantity"] * df["UnitPrice"]
    return df


# =====================================================================
# Phase 3: 聚类 (PCA 散点 + 簇画像)
# =====================================================================
def gen_phase3_viz():
    print("  [Phase 3] Generating viz data...")
    t0 = time.time()
    p3 = load_pkl("phase3_clusters_v3.pkl")

    # PCA scatter (sample 1500 for fast render)
    X_pca = p3.get("X_pca")
    labels = p3.get("labels")
    n = len(labels)
    rng = np.random.default_rng(42)
    if X_pca is not None and n > 1500:
        idx = rng.choice(n, size=1500, replace=False)
        points = [{"x": float(X_pca[i, 0]), "y": float(X_pca[i, 1]), "cluster": int(labels[i])} for i in idx]
    else:
        points = [{"x": float(X_pca[i, 0]), "y": float(X_pca[i, 1]), "cluster": int(labels[i])} for i in range(n)]

    # Cluster profiles (R/F/M medians per cluster)
    with open(os.path.join(PREP, "phase2_preprocessed.pkl"), "rb") as f:
        p2 = pickle.load(f)
    feat = p2["features_df"]
    profiles = []
    for c in sorted(set(labels)):
        mask = labels == c
        if mask.sum() == 0:
            continue
        recency = float(feat.loc[mask, "recency_days"].median())
        orders = float(feat.loc[mask, "total_orders"].median())
        spent = float(feat.loc[feat["CustomerID"].isin(feat.loc[mask, "CustomerID"]), "total_spent"].median()) if "CustomerID" in feat.columns else 0
        # Use the cluster_profiles from pkl if available
        label_text = f"簇 {c}"
        for p in p3.get("cluster_profiles", []):
            if p["cluster"] == c:
                label_text = p.get("business_label", label_text)
                break
        profiles.append({
            "cluster": int(c),
            "label": label_text,
            "size": int(mask.sum()),
            "recency": round(recency, 1),
            "frequency": round(orders, 1),
            "monetary": round(spent, 1),
        })

    out = {
        "metadata": {
            "K": int(p3.get("K", 4)),
            "silhouette": float(p3.get("silhouette", 0)),
            "davies_bouldin": float(p3.get("davies_bouldin", 0)),
            "stability_ari": float(p3.get("stability_ari_mean", 0)),
            "version": p3.get("version", "v4_optuna"),
            "method": p3.get("method", "KMeans"),
        },
        "pca_points": points,
        "cluster_profiles": profiles,
    }
    with open(os.path.join(PREP, "phase3_viz.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, default=str)
    print(f"    {len(points)} points, {len(profiles)} clusters  ({time.time()-t0:.1f}s)")


# =====================================================================
# Phase 4: 流失 (ROC + OOT 时序 + 特征重要性)
# =====================================================================
def gen_phase4_viz():
    print("  [Phase 4] Generating viz data...")
    t0 = time.time()
    p4 = load_pkl("phase4_churn_v5.pkl")
    model = p4.get("churn_model")
    feat_names = p4.get("churn_features", [])

    # Feature importance (from XGBoost model)
    importances = []
    if model is not None and hasattr(model, "feature_importances_"):
        imp = model.feature_importances_
        if len(imp) == len(feat_names):
            for name, val in sorted(zip(feat_names, imp), key=lambda x: -x[1])[:15]:
                importances.append({"feature": name, "importance": round(float(val), 6)})

    # OOT windows (already in pkl)
    oot_windows = []
    for r in p4.get("oot_results", []):
        oot_windows.append({
            "window": r.get("window", ""),
            "auc": round(float(r.get("auc", 0)), 4),
            "n": r.get("n", 0),
            "churn_rate": round(float(r.get("churn_rate", 0)) * 100, 1),
        })

    # ROC curve - need to re-compute by predicting on a test set
    # Use 2011-09-30 cutoff and 80/20 split
    df = load_raw()
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import roc_curve

    TRAIN_END = pd.Timestamp("2011-09-30")
    LABEL_START = pd.Timestamp("2011-10-01")
    df_label = df[df["InvoiceDate"] >= LABEL_START]
    label_customers = set(df_label["CustomerID"].unique())
    df_train = df[df["InvoiceDate"] <= TRAIN_END].copy()
    reference_date = TRAIN_END + pd.Timedelta(days=1)
    max_data_date = df_train["InvoiceDate"].max()

    # Build minimal features matching the pkl training
    feat_df = df_train.groupby("CustomerID").agg(
        total_items=("Quantity", "sum"), total_spent=("LineTotal", "sum"),
        avg_item_price=("UnitPrice", "mean"), price_std=("UnitPrice", "std"),
        price_p25=("UnitPrice", lambda x: x.quantile(0.25)),
        price_cv=("UnitPrice", lambda x: x.std() / max(x.mean(), 0.01)),
        total_orders=("InvoiceNo", "nunique"),
        first_purchase=("InvoiceDate", "min"), last_purchase=("InvoiceDate", "max"),
        unique_products=("StockCode", "nunique"),
    ).reset_index()
    feat_df["purchase_span_days"] = (feat_df["last_purchase"] - feat_df["first_purchase"]).dt.days
    feat_df["avg_purchase_interval"] = np.where(feat_df["total_orders"] > 1, feat_df["purchase_span_days"] / (feat_df["total_orders"] - 1), feat_df["purchase_span_days"])
    feat_df["recency_days"] = (reference_date - feat_df["last_purchase"]).dt.days
    feat_df["tenure_days"] = (reference_date - feat_df["first_purchase"]).dt.days
    feat_df["avg_spend_per_order"] = feat_df["total_spent"] / feat_df["total_orders"]
    feat_df["avg_items_per_order"] = feat_df["total_items"] / feat_df["total_orders"]
    feat_df["spend_per_day"] = feat_df["total_spent"] / np.maximum(feat_df["purchase_span_days"], 1)
    feat_df["items_per_day"] = feat_df["total_items"] / np.maximum(feat_df["purchase_span_days"], 1)
    feat_df["order_frequency"] = feat_df["total_orders"] / np.maximum(feat_df["purchase_span_days"], 1) * 30
    df_train["is_weekend"] = df_train["InvoiceDate"].dt.dayofweek.isin([5, 6]).astype(int)
    wagg = df_train.groupby("CustomerID").agg(w_items=("is_weekend", "sum"), w_total=("is_weekend", "size")).reset_index()
    wagg["weekend_ratio"] = wagg["w_items"] / wagg["w_total"]
    feat_df = feat_df.merge(wagg[["CustomerID", "weekend_ratio"]], on="CustomerID", how="left").fillna({"weekend_ratio": 0})
    df_train["purchase_hour"] = df_train["InvoiceDate"].dt.hour
    hagg = df_train.groupby("CustomerID").agg(
        avg_purchase_hour=("purchase_hour", "mean"), hour_std=("purchase_hour", "std"),
        is_night=("purchase_hour", lambda x: ((x >= 22) | (x <= 5)).mean()),
        is_weekday=("purchase_hour", lambda x: ((x >= 9) & (x <= 17)).mean()),
    ).reset_index()
    feat_df = feat_df.merge(hagg, on="CustomerID", how="left").fillna({"hour_std": 0, "is_night": 0, "is_weekday": 0})
    df_train["purchase_month"] = df_train["InvoiceDate"].dt.month
    magg = df_train.groupby("CustomerID").agg(active_months=("purchase_month", "nunique")).reset_index()
    feat_df = feat_df.merge(magg, on="CustomerID", how="left").fillna({"active_months": 1})
    for window in [30, 60]:
        ce = max_data_date - pd.Timedelta(days=window*2)
        cl = max_data_date - pd.Timedelta(days=window)
        early = df_train[df_train["InvoiceDate"] >= ce]
        late = df_train[df_train["InvoiceDate"] >= cl]
        eo = early.groupby("CustomerID")["InvoiceNo"].nunique().reset_index().rename(columns={"InvoiceNo": f"orders_early_{window}d"})
        lo = late.groupby("CustomerID")["InvoiceNo"].nunique().reset_index().rename(columns={"InvoiceNo": f"orders_late_{window}d"})
        feat_df = feat_df.merge(eo, on="CustomerID", how="left").fillna({f"orders_early_{window}d": 0})
        feat_df = feat_df.merge(lo, on="CustomerID", how="left").fillna({f"orders_late_{window}d": 0})
        feat_df[f"purchase_trend_{window}d"] = feat_df[f"orders_late_{window}d"] / np.maximum(feat_df[f"orders_early_{window}d"], 0.5)
        es = early.groupby("CustomerID")["LineTotal"].sum().reset_index().rename(columns={"LineTotal": f"spend_early_{window}d"})
        ls = late.groupby("CustomerID")["LineTotal"].sum().reset_index().rename(columns={"LineTotal": f"spend_late_{window}d"})
        feat_df = feat_df.merge(es, on="CustomerID", how="left").fillna({f"spend_early_{window}d": 0})
        feat_df = feat_df.merge(ls, on="CustomerID", how="left").fillna({f"spend_late_{window}d": 0})
        feat_df[f"spend_trend_{window}d"] = feat_df[f"spend_late_{window}d"] / np.maximum(feat_df[f"spend_early_{window}d"], 0.5)
    intervals = []
    for cid, group in df_train.groupby("CustomerID"):
        dates = sorted(group["InvoiceDate"].unique())
        if len(dates) > 2:
            ints = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
            intervals.append({"CustomerID": cid, "interval_mean": np.mean(ints), "interval_std": np.std(ints), "interval_cv": np.std(ints) / max(np.mean(ints), 1)})
        else:
            intervals.append({"CustomerID": cid, "interval_mean": 0, "interval_std": 0, "interval_cv": 0})
    feat_df = feat_df.merge(pd.DataFrame(intervals), on="CustomerID", how="left").fillna(0)
    feat_df["purchase_density"] = feat_df["total_orders"] / np.maximum(feat_df["purchase_span_days"], 1)
    feat_df["recent_density_ratio"] = feat_df["purchase_trend_30d"] * feat_df["purchase_density"]
    feat_df["recency_vs_interval"] = feat_df["recency_days"] / np.maximum(feat_df["avg_purchase_interval"], 1)
    feat_df["recency_vs_lifespan"] = feat_df["recency_days"] / np.maximum(feat_df["purchase_span_days"] + feat_df["recency_days"], 1)
    feat_df["recency_ratio"] = feat_df["recency_days"] / np.maximum(feat_df["purchase_span_days"] + feat_df["recency_days"], 1)
    feat_df["purchase_consistency"] = 1 / (1 + feat_df["avg_purchase_interval"])
    feat_df["diversity_x_freq"] = feat_df["unique_products"] * feat_df["order_frequency"]
    feat_df["spend_depth"] = feat_df["avg_spend_per_order"] / np.maximum(feat_df["avg_item_price"], 0.01)
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
    feat_df = feat_df.merge(pd.DataFrame(rel), on="CustomerID", how="left").fillna(0)
    feat_df["activity_rate"] = feat_df["active_months"] / np.maximum(feat_df["purchase_span_days"] / 30, 1)
    feat_df["engagement_consistency"] = feat_df["active_months"] / np.maximum(feat_df["purchase_span_days"] / 30, 1)
    feat_df["is_bulk_buyer"] = (feat_df["avg_items_per_order"] > feat_df["avg_items_per_order"].quantile(0.9)).astype(int)
    feat_df["product_diversity"] = feat_df["unique_products"] / feat_df["total_orders"]
    feat_df["spending_cv"] = feat_df["price_std"] / np.maximum(feat_df["avg_item_price"], 0.01)
    feat_df["price_range"] = feat_df["price_p25"] * 2
    feat_df["is_churn"] = (~feat_df["CustomerID"].isin(label_customers)).astype(int)
    feat_df["recency_score"] = np.minimum(100, (feat_df["recency_days"] / 365) * 100)
    feat_df["expected_next_purchase"] = feat_df["last_purchase"] + pd.to_timedelta(feat_df["avg_purchase_interval"], unit="D")
    feat_df["days_overdue"] = (reference_date - feat_df["expected_next_purchase"]).dt.days.clip(lower=0)
    feat_df["overdue_score"] = np.where(feat_df["days_overdue"] > 0, np.minimum(100, np.maximum(0, feat_df["days_overdue"] / 180) * 100), 0)
    feat_df["low_engagement_score"] = (1 - feat_df["engagement_consistency"]) * 50

    CHURN_EXCLUDE = ["churn_risk_score", "is_churn", "is_at_risk", "loyalty_index", "purchase_span_days",
                     "purchase_trend_30d", "spend_trend_30d", "purchase_trend_60d", "spend_trend_60d",
                     "recent_density_ratio"]
    if not feat_names:
        feat_names = [c for c in feat_df.columns if c not in CHURN_EXCLUDE + ["CustomerID", "is_churn",
                                                                              "first_purchase", "last_purchase", "expected_next_purchase"]]

    X = feat_df[feat_names].fillna(0).values
    y = feat_df["is_churn"].values
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    # ROC curve from test predictions
    roc_points = []
    test_auc = 0.0
    if model is not None:
        try:
            yp = model.predict_proba(X_te)[:, 1]
            fpr, tpr, _ = roc_curve(y_te, yp)
            test_auc = float(np.trapz(tpr, fpr))  # AUC via trapezoid
            # Downsample to 50 points for compact JSON
            n_pts = len(fpr)
            if n_pts > 50:
                idx = np.linspace(0, n_pts - 1, 50).astype(int)
                roc_points = [{"fpr": round(float(fpr[i]), 4), "tpr": round(float(tpr[i]), 4)} for i in idx]
            else:
                roc_points = [{"fpr": round(float(fpr[i]), 4), "tpr": round(float(tpr[i]), 4)} for i in range(n_pts)]
        except Exception as e:
            print(f"    ROC compute failed: {e}")

    out = {
        "metadata": {
            "test_auc": round(float(p4.get("test_auc", test_auc)), 4),
            "oot_mean_auc": round(float(p4.get("oot_mean_auc", 0)), 4),
            "n_features": len(feat_names),
            "model_type": "XGBoost+Optuna" if "optuna_best_params" in p4 else "XGBoost",
            "version": p4.get("version", "unknown"),
            "_auc_source": "pkl.temporal" if p4.get("test_auc") else "viz.random_split",
        },
        "roc_curve": roc_points,
        "oot_windows": oot_windows,
        "feature_importance": importances,
    }
    with open(os.path.join(PREP, "phase4_viz.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, default=str)
    print(f"    {len(roc_points)} ROC pts, {len(oot_windows)} OOT windows, {len(importances)} features  ({time.time()-t0:.1f}s)")


# =====================================================================
# Phase 5: 销售预测 (实际vs预测 + 残差 + 季节性)
# =====================================================================
def gen_phase5_viz():
    print("  [Phase 5] Generating viz data...")
    t0 = time.time()
    p5 = load_pkl("phase5_forecast_v2.pkl")

    # Re-build weekly series (same as build_winner.py)
    df = load_raw()
    df["year_week"] = df["InvoiceDate"].dt.to_period("W-MON")
    weekly = df.groupby("year_week").agg(revenue=("LineTotal", "sum"),
                                          orders=("InvoiceNo", "nunique"),
                                          customers=("CustomerID", "nunique"),
                                          quantity=("Quantity", "sum")).reset_index()
    weekly["date"] = weekly["year_week"].dt.to_timestamp()
    weekly = weekly.drop(columns=["year_week"]).sort_values("date").reset_index(drop=True)

    # Build features (same as v3)
    uk_holidays = pd.to_datetime([
        "2010-01-01", "2010-04-02", "2010-04-05", "2010-05-03", "2010-05-31",
        "2010-08-30", "2010-12-27", "2010-12-28",
        "2011-01-03", "2011-04-22", "2011-04-25", "2011-05-02", "2011-05-30",
        "2011-08-29", "2011-12-26", "2011-12-27",
        "2010-11-26", "2011-11-25", "2010-12-25", "2011-12-25",
        "2010-11-11", "2011-11-11",
    ])

    def build_features(ts_df, target_col="revenue"):
        df_feat = ts_df.copy().sort_values("date").reset_index(drop=True)
        lags = [1, 2, 4, 8, 12]
        windows = [4, 8, 12]
        for lag in lags:
            df_feat[f"lag_{lag}"] = df_feat[target_col].shift(lag)
        for window in windows:
            df_feat[f"roll_mean_{window}"] = df_feat[target_col].rolling(window=window).mean()
            df_feat[f"roll_std_{window}"] = df_feat[target_col].rolling(window=window).std()
            df_feat[f"roll_max_{window}"] = df_feat[target_col].rolling(window=window).max()
            df_feat[f"roll_min_{window}"] = df_feat[target_col].rolling(window=window).min()
        df_feat["year"] = df_feat["date"].dt.year
        df_feat["month"] = df_feat["date"].dt.month
        df_feat["quarter"] = df_feat["date"].dt.quarter
        df_feat["week_of_year"] = df_feat["date"].dt.isocalendar().week.astype(int)
        df_feat["time_idx"] = np.arange(len(df_feat))
        df_feat["growth_1"] = df_feat[target_col].pct_change(1).replace([np.inf, -np.inf], 0).fillna(0)
        df_feat["days_to_christmas"] = ((pd.to_datetime(df_feat["date"].dt.year.astype(str) + "-12-25") - df_feat["date"]).dt.days).clip(-30, 365)
        df_feat["is_christmas_season"] = ((df_feat["month"] >= 11) & (df_feat["month"] <= 12)).astype(int)
        df_feat["is_jan_sale"] = ((df_feat["month"] == 1)).astype(int)
        df_feat["is_black_friday_week"] = ((df_feat["month"] == 11) & (df_feat["week_of_year"] >= 47)).astype(int)
        df_feat["has_holiday"] = 0
        for hd in uk_holidays:
            df_feat.loc[abs((df_feat["date"] - hd).dt.days) <= 7, "has_holiday"] = 1
        df_feat["month_sin"] = np.sin(2 * np.pi * df_feat["month"] / 12)
        df_feat["month_cos"] = np.cos(2 * np.pi * df_feat["month"] / 12)
        df_feat["woy_sin"] = np.sin(2 * np.pi * df_feat["week_of_year"] / 52)
        df_feat["woy_cos"] = np.cos(2 * np.pi * df_feat["week_of_year"] / 52)
        df_feat["is_month_end"] = (df_feat["date"].dt.day >= 25).astype(int)
        df_feat["is_xmas_peak"] = ((df_feat["week_of_year"] >= 49) & (df_feat["week_of_year"] <= 52)).astype(int)
        max_lag = max(lags)
        df_feat = df_feat.iloc[max_lag:].copy().reset_index(drop=True)
        return df_feat

    df_feat = build_features(weekly)
    feature_cols = [c for c in df_feat.columns if c not in ["date", "revenue"]]
    X = df_feat[feature_cols].values
    y = df_feat["revenue"].values
    SPLIT = len(X) - 8
    X_tr, X_te = X[:SPLIT], X[SPLIT:]
    y_tr, y_te = y[:SPLIT], y[SPLIT:]

    # Get predictions
    model = p5.get("model")
    if model is None:
        print("    No model in pkl, skipping")
        return
    pred = np.clip(model.predict(X_te), 0, None)
    test_dates = df_feat["date"].iloc[SPLIT:].tolist()

    # Actual vs pred (8 weeks)
    actual_pred = [{
        "date": d.strftime("%Y-%m-%d"),
        "actual": round(float(y_te[i]), 0),
        "predicted": round(float(pred[i]), 0),
    } for i, d in enumerate(test_dates)]

    # Residual histogram (15 bins)
    residuals = y_te - pred
    hist, bin_edges = np.histogram(residuals, bins=15)
    residual_hist = [{
        "bin": f"{int(bin_edges[i])}~{int(bin_edges[i+1])}",
        "count": int(hist[i]),
        "center": int((bin_edges[i] + bin_edges[i+1]) / 2),
    } for i in range(len(hist))]

    # Seasonality: monthly average revenue across all weeks
    monthly_avg = weekly.groupby(weekly["date"].dt.month)["revenue"].mean().to_dict()
    seasonality = [{
        "month": int(m),
        "avg_revenue": round(float(v), 0),
        "month_name": ["", "1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"][m],
    } for m, v in sorted(monthly_avg.items())]

    out = {
        "metadata": {
            "test_smape": round(float(p5.get("test_smape", 0)), 2),
            "test_mape": round(float(p5.get("test_mape", 0)), 2),
            "n_features": len(feature_cols),
            "model_type": "LightGBM+UK 日历",
            "version": p5.get("version", "unknown"),
        },
        "actual_pred": actual_pred,
        "residual_hist": residual_hist,
        "seasonality": seasonality,
    }
    with open(os.path.join(PREP, "phase5_viz.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, default=str)
    print(f"    {len(actual_pred)} test weeks, {len(residual_hist)} residual bins, {len(seasonality)} months  ({time.time()-t0:.1f}s)")


# =====================================================================
# Phase 6: 关联规则 (Top 20 + 散点矩阵)
# =====================================================================
def gen_phase6_viz():
    print("  [Phase 6] Generating viz data...")
    t0 = time.time()
    p6 = load_pkl("phase6_association_v2.pkl")

    # Top 20 rules by lift
    top_rules = p6.get("global_rules", {}).get("top_rules", [])[:20]
    top_rules_simple = [{
        "antecedent": ", ".join(r["antecedents"]) if isinstance(r["antecedents"], list) else str(r["antecedents"]),
        "consequent": ", ".join(r["consequents"]) if isinstance(r["consequents"], list) else str(r["consequents"]),
        "support": round(float(r["support"]) * 100, 2),
        "confidence": round(float(r["confidence"]) * 100, 2),
        "lift": round(float(r["lift"]), 2),
    } for r in top_rules]

    # Scatter: sample 500 rules from global rules (use all if <500)
    all_rules = p6.get("global_rules", {}).get("top_rules", [])
    if len(all_rules) > 500:
        rng = np.random.default_rng(42)
        sample_idx = rng.choice(len(all_rules), size=500, replace=False)
        scatter = [{
            "support": round(float(all_rules[i]["support"]) * 100, 3),
            "confidence": round(float(all_rules[i]["confidence"]) * 100, 2),
            "lift": round(float(all_rules[i]["lift"]), 2),
            "label": ", ".join(all_rules[i]["antecedents"])[:30] if isinstance(all_rules[i]["antecedents"], list) else str(all_rules[i]["antecedents"])[:30],
        } for i in sample_idx]
    else:
        scatter = [{
            "support": round(float(r["support"]) * 100, 3),
            "confidence": round(float(r["confidence"]) * 100, 2),
            "lift": round(float(r["lift"]), 2),
            "label": ", ".join(r["antecedents"])[:30] if isinstance(r["antecedents"], list) else str(r["antecedents"])[:30],
        } for r in all_rules]

    out = {
        "metadata": {
            "n_global_rules": int(p6.get("global_rules", {}).get("n_rules", 0)),
            "mean_lift": round(float(p6.get("global_rules", {}).get("mean_lift", 0)), 2),
            "n_stockcode_rules": int(p6.get("stockcode_rules", {}).get("n_rules", 0)),
            "n_cluster_rules": sum(int(c.get("n_rules", 0)) for c in p6.get("cluster_rules", {}).values()),
            "version": p6.get("metadata", {}).get("version", "unknown"),
        },
        "top_rules": top_rules_simple,
        "scatter": scatter,
        "cluster_summary": [{
            "cluster": int(c["cluster"]) if "cluster" in c else int(k),
            "size": c.get("n_customers", 0),
            "n_rules": c.get("n_rules", 0),
            "mean_lift": round(float(c.get("mean_lift", 0)), 2),
        } for k, c in (p6.get("cluster_rules", {}) or {}).items()],
    }
    with open(os.path.join(PREP, "phase6_viz.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, default=str)
    print(f"    {len(top_rules_simple)} top rules, {len(scatter)} scatter points, {len(out['cluster_summary'])} clusters  ({time.time()-t0:.1f}s)")


if __name__ == "__main__":
    print("=" * 60)
    print("  ShopMiner — Generate Model Viz Data")
    print("=" * 60)
    gen_phase3_viz()
    gen_phase4_viz()
    gen_phase5_viz()
    gen_phase6_viz()
    print("\nDone. Saved to:")
    for m in ["phase3", "phase4", "phase5", "phase6"]:
        f_path = os.path.join(PREP, f"{m}_viz.json")
        if os.path.exists(f_path):
            size = os.path.getsize(f_path) / 1024
            print(f"  {f_path}  ({size:.1f} KB)")
