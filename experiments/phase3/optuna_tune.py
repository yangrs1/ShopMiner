"""
Phase 3 Optuna: Tune MiniBatchKMeans for Silhouette.
- Tune: K, batch_size, n_init, max_iter, init, max_no_improvement
- Objective: silhouette_score (with mini-batch sub-sample for speed)
- Final: re-run on full normal set + stability
"""
import os, sys, warnings, pickle, json, time
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

import optuna
from optuna.samplers import TPESampler
optuna.logging.set_verbosity(optuna.logging.WARNING)

from sklearn.cluster import MiniBatchKMeans, KMeans
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import silhouette_score, davies_bouldin_score, adjusted_rand_score
from sklearn.decomposition import PCA

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PREP = os.path.join(ROOT, "data", "prep")
EXP = os.path.join(ROOT, "experiments", "phase3")

# ─── Build features (replicate v3 build_winner.py) ───
print("[1/4] Building RFM features...")
t0 = time.time()
with open(os.path.join(PREP, "phase2_preprocessed.pkl"), "rb") as f:
    p2 = pickle.load(f)
features_df = p2["features_df"].copy()

rfm = features_df[["CustomerID"]].copy()
rfm["R_Score"] = 5 - pd.qcut(features_df["recency_days"], 5, labels=False, duplicates="drop")
rfm["F_Score"] = pd.qcut(features_df["total_orders"], 5, labels=False, duplicates="drop") + 1
rfm["M_Score"] = pd.qcut(features_df["total_spent"], 5, labels=False, duplicates="drop") + 1
rfm["R_Score"] += 1
rfm["product_diversity"] = features_df["unique_products"]
rfm["is_bulk_buyer"] = (features_df["avg_items_per_order"] > features_df["avg_items_per_order"].median()).astype(int)
rfm["purchase_velocity"] = features_df["total_orders"] / features_df["purchase_span_days"].clip(lower=1)
rfm["activity_rate"] = features_df["total_orders"] / features_df["purchase_span_days"].clip(lower=1)
rfm["weekend_ratio"] = features_df["weekend_ratio"]
rfm["avg_spend_per_order"] = features_df["avg_spend_per_order"]
rfm["total_orders"] = features_df["total_orders"]
rfm["total_spent"] = features_df["total_spent"]
rfm["recency_days"] = features_df["recency_days"]

FEATS = ["R_Score", "F_Score", "M_Score", "product_diversity", "is_bulk_buyer",
         "purchase_velocity", "activity_rate", "weekend_ratio",
         "avg_spend_per_order", "total_orders", "recency_days"]
X_raw = rfm[FEATS].fillna(rfm[FEATS].median()).values
X_log = np.log1p(X_raw)
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X_log)

# Outlier removal (same as v3)
km_temp = KMeans(n_clusters=5, random_state=42, n_init=20)
temp_labels = km_temp.fit_predict(X_scaled)
sizes = pd.Series(temp_labels).value_counts()
out_ids = [c for c, s in sizes.items() if s < 50]
out_mask = np.isin(temp_labels, out_ids)
norm_mask = ~out_mask
X_normal = X_scaled[norm_mask]
normal_idx = np.where(norm_mask)[0]
outlier_idx = np.where(out_mask)[0]
n_out = int(out_mask.sum())
print(f"  Customers: {len(features_df)}  Normal: {norm_mask.sum()}  Outliers: {n_out}  Time: {time.time()-t0:.1f}s")

# Use a 1500-row subsample for fast Optuna eval (silhouette is O(n^2))
RNG = np.random.default_rng(42)
SAMPLE_IDX = RNG.choice(len(X_normal), size=min(1500, len(X_normal)), replace=False)
X_sub = X_normal[SAMPLE_IDX]

# ─── Optuna objective: maximize silhouette on subsample ───
print("\n[2/4] Optuna search (50 trials, maximize Silhouette)...")
t0 = time.time()
def objective(trial):
    K = trial.suggest_int("K", 3, 8)
    params = {
        "n_clusters": K,
        "batch_size": trial.suggest_categorical("batch_size", [64, 128, 256, 512]),
        "n_init": trial.suggest_int("n_init", 5, 30),
        "max_iter": trial.suggest_int("max_iter", 100, 500, step=50),
        "init": trial.suggest_categorical("init", ["k-means++", "random"]),
        "max_no_improvement": trial.suggest_int("max_no_improvement", 5, 30),
        "random_state": 42,
        "reassignment_ratio": trial.suggest_float("reassignment_ratio", 0.0, 0.1),
    }
    m = MiniBatchKMeans(**params)
    labels = m.fit_predict(X_sub)
    if len(set(labels)) < 2:
        return -1.0
    return float(silhouette_score(X_sub, labels))

study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=42))
study.optimize(objective, n_trials=50, show_progress_bar=False)
print(f"  Best sub-silhouette: {study.best_value:.4f}")
print(f"  Best params: {study.best_params}")
print(f"  Time: {time.time()-t0:.1f}s")

# ─── Train final on full normal set with best params ───
print("\n[3/4] Training final on full normal set...")
t0 = time.time()
best = study.best_params.copy()
K_final = best.pop("K")
m_final = MiniBatchKMeans(n_clusters=K_final, **best, random_state=42)
labels_normal = m_final.fit_predict(X_normal)
sil = float(silhouette_score(X_normal, labels_normal))
db = float(davies_bouldin_score(X_normal, labels_normal))
print(f"  Final: K={K_final}  Sil={sil:.4f}  DB={db:.4f}  Time: {time.time()-t0:.1f}s")

# Stability (ARI bootstrap)
ari_list = []
for i in range(30):
    idx = np.random.choice(len(X_normal), size=len(X_normal), replace=True)
    boot = KMeans(n_clusters=K_final, random_state=42 + i, n_init=10)
    boot_l = boot.fit_predict(X_normal[idx])
    if len(set(boot_l)) >= 2:
        ari_list.append(adjusted_rand_score(labels_normal[idx], boot_l))
ari_mean = float(np.mean(ari_list)) if ari_list else 0.0
ari_std = float(np.std(ari_list)) if ari_list else 0.0
print(f"  ARI: {ari_mean:.4f} ± {ari_std:.4f}")

# ─── Compare ───
print("\n[4/4] Loading current v3 winner...")
with open(os.path.join(PREP, "phase3_clusters_v3.pkl"), "rb") as f:
    v3 = pickle.load(f)
v3_sil = v3.get("silhouette", 0.360)
v3_db = v3.get("davies_bouldin", 1.067)
v3_K = v3.get("K", 4)
print(f"  Current: K={v3_K}  Sil={v3_sil:.4f}  DB={v3_db:.4f}")
print(f"  New:     K={K_final}  Sil={sil:.4f}  DB={db:.4f}")

# ─── Save if improved (silhouette is the primary metric) ───
if sil > v3_sil:
    print(f"\n[SAVE] Silhouette improved ({v3_sil:.4f} -> {sil:.4f})...")
    final_labels = np.full(len(features_df), -1, dtype=int)
    final_labels[normal_idx] = labels_normal
    final_labels[outlier_idx] = 999
    pca_vis = PCA(n_components=2).fit_transform(X_scaled)

    # Build business labels
    global_spent = features_df["total_spent"].median()
    cluster_profiles = []
    for c in sorted(set(final_labels)):
        mask = final_labels == c
        size = int(mask.sum())
        if size == 0: continue
        recency = float(features_df.loc[features_df.index[mask], "recency_days"].median())
        orders = float(features_df.loc[features_df.index[mask], "total_orders"].median())
        spent = float(features_df.loc[features_df.index[mask], "total_spent"].median())
        if c == 999:
            label = "超多样化客户"
        elif recency <= 30 and orders >= 8:
            label = "忠诚客户"
        elif recency <= 45 and orders >= 4 and spent >= global_spent:
            label = "高价值忠诚客户"
        elif recency <= 60 and orders >= 3:
            label = "一般活跃客户"
        elif recency > 180 and spent < global_spent * 0.3:
            label = "深度流失客户"
        elif recency > 180:
            label = "低频流失客户"
        elif recency > 120:
            label = "流失预警客户"
        elif spent >= global_spent * 1.5:
            label = "高消费低频客户"
        elif orders <= 2 and recency <= 90:
            label = "新客户"
        else:
            label = "普通客户"
        cluster_profiles.append({"cluster": int(c), "size": size,
                                  "pct": size / len(final_labels) * 100,
                                  "business_label": label})

    save_data = {
        "method": "MiniBatchKMeans(log1p+MinMax+Optuna)",
        "K": K_final,
        "silhouette": sil,
        "davies_bouldin": db,
        "calinski_harabasz": 0,
        "labels": final_labels,
        "customer_ids": features_df["CustomerID"].tolist(),
        "X_pca": pca_vis,
        "cluster_features": FEATS,
        "cluster_profiles": cluster_profiles,
        "comparison_results": [("MiniBatchKMeans(log1p+MinMax+Optuna)", sil, db, 0)],
        "stability_ari_mean": ari_mean,
        "stability_ari_std": ari_std,
        "outlier_ids": features_df.iloc[outlier_idx]["CustomerID"].tolist() if n_out > 0 else [],
        "n_outliers": n_out,
        "scaler": scaler,
        "optuna_best_params": study.best_params,
        "improvement_note": f"v4: Optuna-tuned MiniBatchKMeans, Sil {v3_sil:.4f} -> {sil:.4f} ({(sil-v3_sil)/v3_sil*100:+.2f}%)",
    }
    out_pkl = os.path.join(EXP, "phase3_clusters_winner.pkl")
    with open(out_pkl, "wb") as f:
        pickle.dump(save_data, f)
    print(f"  Saved: {out_pkl}")
else:
    print(f"\n[NO SAVE] Silhouette not improved ({sil:.4f} <= {v3_sil:.4f}). Keep v3.")

study_out = {
    "best_value_sub_sil": study.best_value,
    "best_params": study.best_params,
    "final_K": K_final,
    "final_sil": sil,
    "final_db": db,
    "ari_mean": ari_mean,
    "ari_std": ari_std,
    "sil_improved": bool(sil > v3_sil),
    "baseline_sil": v3_sil,
}
with open(os.path.join(EXP, "phase3_optuna.json"), "w") as f:
    json.dump(study_out, f, indent=2, ensure_ascii=False, default=str)
print(f"\nStudy saved: {os.path.join(EXP, 'phase3_optuna.json')}")
