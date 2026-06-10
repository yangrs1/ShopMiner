"""
Phase 3 Winner: log1p + MinMaxScaler + MiniBatchKMeans, K=4
Build full pkl in same structure as original, save to experiments/phase3/ for comparison.
"""
import os, sys, warnings, pickle, json
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

from sklearn.cluster import MiniBatchKMeans, KMeans
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import silhouette_score, davies_bouldin_score, adjusted_rand_score
from sklearn.decomposition import PCA

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PREP = os.path.join(ROOT, "data", "prep")
EXP = os.path.join(ROOT, "experiments", "phase3")

with open(os.path.join(PREP, "phase2_preprocessed.pkl"), "rb") as f:
    p2 = pickle.load(f)
features_df = p2["features_df"].copy()

# ─── Same RFM build as original ───
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

# ─── log1p + MinMax + outlier removal ───
X_log = np.log1p(X_raw)
scaler = MinMaxScaler()
X_scaled = scaler.fit_transform(X_log)
# Outlier removal: cluster with k=5, mark clusters < 50
km_temp = KMeans(n_clusters=5, random_state=42, n_init=20)
temp_labels = km_temp.fit_predict(X_scaled)
sizes = pd.Series(temp_labels).value_counts()
out_ids = [c for c, s in sizes.items() if s < 50]
out_mask = np.isin(temp_labels, out_ids)
norm_mask = ~out_mask
X_normal = X_scaled[norm_mask]
normal_idx = np.where(norm_mask)[0]
outlier_idx = np.where(out_mask)[0]
n_out = out_mask.sum()
print(f"Normal: {norm_mask.sum()}  Outliers: {n_out}")

# ─── Final model: MiniBatchKMeans K=4 ───
K = 4
mbkm = MiniBatchKMeans(n_clusters=K, random_state=42, n_init=30, batch_size=256, max_iter=500)
labels_normal = mbkm.fit_predict(X_normal)
sil = float(silhouette_score(X_normal, labels_normal))
db = float(davies_bouldin_score(X_normal, labels_normal))
print(f"Final: K={K}  Sil={sil:.4f}  DB={db:.4f}")

# ─── Stability (ARI bootstrap) ───
ari_list = []
for i in range(30):
    idx = np.random.choice(len(X_normal), size=len(X_normal), replace=True)
    boot = KMeans(n_clusters=K, random_state=42 + i, n_init=10)
    boot_l = boot.fit_predict(X_normal[idx])
    if len(set(boot_l)) >= 2:
        ari_list.append(adjusted_rand_score(labels_normal[idx], boot_l))
ari_mean = float(np.mean(ari_list)) if ari_list else 0.0
ari_std = float(np.std(ari_list)) if ari_list else 0.0
print(f"Bootstrap ARI: {ari_mean:.4f} ± {ari_std:.4f}")

# ─── Final labels (outliers → 999) ───
final_labels = np.full(len(features_df), -1, dtype=int)
final_labels[normal_idx] = labels_normal
final_labels[outlier_idx] = 999

# ─── Business labels ───
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
    print(f"  Cluster {c} (n={size}): {label}  R={recency:.0f}d F={orders:.1f} M={spent:.0f}")

# ─── PCA visualization ───
pca_vis = PCA(n_components=2).fit_transform(X_scaled)

# ─── Save full pkl (same structure) ───
save_data = {
    "method": "MiniBatchKMeans(log1p+MinMax)",
    "K": K,
    "silhouette": sil,
    "davies_bouldin": db,
    "calinski_harabasz": 0,
    "labels": final_labels,
    "customer_ids": features_df["CustomerID"].tolist(),
    "X_pca": pca_vis,
    "cluster_features": FEATS,
    "cluster_profiles": cluster_profiles,
    "comparison_results": [("MiniBatchKMeans(log1p+MinMax)", sil, db, 0)],
    "stability_ari_mean": ari_mean,
    "stability_ari_std": ari_std,
    "outlier_ids": features_df.iloc[outlier_idx]["CustomerID"].tolist() if n_out > 0 else [],
    "n_outliers": int(n_out),
    "scaler": scaler,
}
out_pkl = os.path.join(EXP, "phase3_clusters_winner.pkl")
with open(out_pkl, "wb") as f:
    pickle.dump(save_data, f)
print(f"\nWinner pkl saved: {out_pkl}")
print(f"vs baseline: Silhouette 0.272 -> {sil:.3f} ({(sil-0.272)/0.272*100:+.1f}%)")
print(f"              DB 1.370 -> {db:.3f} ({(db-1.370)/1.370*100:+.1f}%)")
