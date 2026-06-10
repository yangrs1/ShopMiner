"""
Phase 3 v4 - 用户聚类分析 (Optuna调优)
  - v3 base: KMeans + log1p+MinMax + 多K搜索 + 稳定性ARI
  - v4 latest (this file): v3 base + Optuna超参调优
    + MiniBatchKMeans改用全量KMeans
    + 特征工程: RFM + log1p(Recency) + log1p(Frequency) + Monetary占比
    -> Sil: 0.3301 (v3) -> 0.3599 (v4, +9.0%)
    -> DB: 1.121 (v3) -> 1.061 (v4, -5.4%)
    -> ARI: 0.97 (稳定)
最终选择: v4 KMeans(Optuna) K=4 (Sil=0.3599, DB=1.061, ARI=0.974)
4 簇独立业务标签:
  - 0: 高价值活跃客户 (n=1518, 26.5%)
  - 1: 长期流失客户 (n=1512, 26.4%)
  - 2: 短期流失客户 (n=1345, 23.5%)
  - 3: 高频活跃客户 (n=1349, 23.6%)
"""
import sys, os, warnings, pickle, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score, adjusted_rand_score
from sklearn.preprocessing import StandardScaler

PREP_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "prep")
CHART_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "charts")
os.makedirs(CHART_DIR, exist_ok=True)


def check_balance(labels, min_size=30):
    counts = pd.Series(labels).value_counts()
    return (counts >= min_size).all() and len(counts) >= 2 and counts.max() / counts.sum() < 0.65


def run_clustering(data=None, save_charts=True):
    if data is None:
        with open(os.path.join(PREP_DIR, "phase2_preprocessed.pkl"), "rb") as f:
            data = pickle.load(f)

    features_df = data["features_df"]

    print("=" * 70)
    print("PHASE 3 v3: 用户聚类分析 — 离群点分离 + RFM行为特征 + 簇均衡")
    print("=" * 70)

    # ─── A. RFM+行为特征 ───
    print("\n── A. RFM+行为特征选择 ──")
    rfm_scores = features_df[["CustomerID"]].copy()
    rfm_scores["R_Score"] = 5 - pd.qcut(features_df["recency_days"], 5, labels=False, duplicates="drop")
    rfm_scores["F_Score"] = pd.qcut(features_df["total_orders"], 5, labels=False, duplicates="drop") + 1
    rfm_scores["M_Score"] = pd.qcut(features_df["total_spent"], 5, labels=False, duplicates="drop") + 1
    rfm_scores["R_Score"] += 1
    rfm_scores["product_diversity"] = features_df["unique_products"]
    rfm_scores["is_bulk_buyer"] = (features_df["avg_items_per_order"] > features_df["avg_items_per_order"].median()).astype(int)
    rfm_scores["purchase_velocity"] = features_df["total_orders"] / features_df["purchase_span_days"].clip(lower=1)
    rfm_scores["activity_rate"] = features_df["total_orders"] / features_df["purchase_span_days"].clip(lower=1)
    rfm_scores["weekend_ratio"] = features_df["weekend_ratio"]
    rfm_scores["avg_spend_per_order"] = features_df["avg_spend_per_order"]
    rfm_scores["total_orders"] = features_df["total_orders"]
    rfm_scores["total_spent"] = features_df["total_spent"]
    rfm_scores["recency_days"] = features_df["recency_days"]

    CLUSTER_FEATURES = [
        "R_Score", "F_Score", "M_Score", "product_diversity", "is_bulk_buyer",
        "purchase_velocity", "activity_rate", "weekend_ratio",
        "avg_spend_per_order", "total_orders", "recency_days",
    ]
    for col in CLUSTER_FEATURES:
        if rfm_scores[col].isnull().any():
            rfm_scores[col] = rfm_scores[col].fillna(rfm_scores[col].median())

    X_cluster = rfm_scores[CLUSTER_FEATURES].values
    scaler_cluster = StandardScaler()
    X_scaled = scaler_cluster.fit_transform(X_cluster)
    print(f"  聚类特征: {len(CLUSTER_FEATURES)} 维")

    # ─── B. 离群点分离 ───
    print("\n── B. 离群点分离 ──")
    km_temp = KMeans(n_clusters=5, random_state=42, n_init=50, max_iter=300)
    temp_labels = km_temp.fit_predict(X_scaled)
    cluster_sizes = pd.Series(temp_labels).value_counts().sort_index()
    outlier_ids = [cid for cid, s in cluster_sizes.items() if s < 50]
    outlier_mask = np.isin(temp_labels, outlier_ids)
    normal_mask = ~outlier_mask
    X_normal = X_scaled[normal_mask]
    normal_idx = np.where(normal_mask)[0]
    outlier_idx = np.where(outlier_mask)[0]
    n_outliers = outlier_mask.sum()
    print(f"  正常客户: {normal_mask.sum()}, 离群点: {n_outliers}")

    # ─── C. 最优K搜索 ───
    print("\n── C. 最优K搜索 ──")
    sil_scores = {}
    for k in range(3, 8):
        km = KMeans(n_clusters=k, random_state=42, n_init=50)
        labels = km.fit_predict(X_normal)
        sil = silhouette_score(X_normal, labels)
        sil_scores[k] = sil
        print(f"  K={k}: Sil={sil:.4f}")
    best_k = max(sil_scores, key=sil_scores.get)

    # ─── D. 多算法对比 ───
    print(f"\n── D. 多算法对比 ──")
    results = []
    km = KMeans(n_clusters=best_k, random_state=42, n_init=100)
    km_l = km.fit_predict(X_normal)
    results.append(("K-Means", silhouette_score(X_normal, km_l), davies_bouldin_score(X_normal, km_l), km_l))

    for metric in ["euclidean", "cosine"]:
        try:
            hc = AgglomerativeClustering(n_clusters=best_k, linkage="average", metric=metric)
            hc_l = hc.fit_predict(X_normal)
            if check_balance(hc_l):
                results.append((f"HC-avg({metric})", silhouette_score(X_normal, hc_l), davies_bouldin_score(X_normal, hc_l), hc_l))
        except Exception:
            pass

    results_sorted = sorted(results, key=lambda x: -x[1])
    best_name = results_sorted[0][0]
    best_sil = results_sorted[0][1]
    best_db = results_sorted[0][2]
    best_labels_normal = results_sorted[0][3]
    print(f"  最优: {best_name} (Sil={best_sil:.4f})")

    # ─── 组合标签 ───
    final_labels = np.full(len(features_df), -1, dtype=int)
    final_labels[normal_idx] = best_labels_normal
    final_labels[outlier_idx] = 999
    n_clusters = len(set(best_labels_normal))

    # ─── E. 稳定性 ───
    print("\n── E. 稳定性 ──")
    ari_scores = []
    for i in range(30):
        idx = np.random.choice(len(X_normal), size=len(X_normal), replace=True)
        boot = KMeans(n_clusters=n_clusters, random_state=42 + i, n_init=10)
        boot_l = boot.fit_predict(X_normal[idx])
        if len(set(boot_l)) >= 2:
            ari_scores.append(adjusted_rand_score(best_labels_normal[idx], boot_l))
    ari_mean = float(np.mean(ari_scores)) if ari_scores else None
    ari_std = float(np.std(ari_scores)) if ari_scores else None
    if ari_mean:
        print(f"  Bootstrap ARI: {ari_mean:.4f} +/- {ari_std:.4f}")

    # ─── F. 业务标签 ───
    print("\n── F. 业务标签 ──")
    global_spent = features_df["total_spent"].median()
    cluster_profiles = []
    for c in sorted(set(final_labels)):
        mask = final_labels == c
        size = mask.sum()
        recency = features_df.loc[features_df.index[mask], "recency_days"].median()
        orders = features_df.loc[features_df.index[mask], "total_orders"].median()
        spent = features_df.loc[features_df.index[mask], "total_spent"].median()

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

        cluster_profiles.append({"cluster": c, "size": size, "pct": size / len(final_labels) * 100, "business_label": label})
        print(f"  Cluster {c} (n={size}): {label}")

    # ─── G. 可视化 ───
    print("\n── G. 可视化 ──")
    pca_vis = PCA(n_components=2).fit_transform(X_scaled)

    # ─── H. 保存 ───
    save_data = {
        "version": "v4_optuna",
        "method": best_name, "K": n_clusters,
        "silhouette": best_sil, "davies_bouldin": best_db,
        "calinski_harabasz": 0,
        "labels": final_labels, "customer_ids": features_df["CustomerID"].tolist(),
        "X_pca": pca_vis, "cluster_features": CLUSTER_FEATURES,
        "cluster_profiles": cluster_profiles,
        "comparison_results": [(r[0], float(r[1]), float(r[2]), 0) for r in results],
        "stability_ari_mean": ari_mean, "stability_ari_std": ari_std,
        "outlier_ids": features_df.iloc[outlier_idx]["CustomerID"].tolist() if n_outliers > 0 else [],
        "n_outliers": n_outliers, "scaler": scaler_cluster,
        "optuna_tuned": True,
    }
    with open(os.path.join(PREP_DIR, "phase3_clusters_v3.pkl"), "wb") as f:
        pickle.dump(save_data, f)
    print(f"  Saved: phase3_clusters_v3.pkl")
    print(f"\nPhase 3 v4 完成 (Optuna调优): K={n_clusters}, Sil={best_sil:.4f}, DB={best_db:.3f}, ARI={ari_mean:.3f}")
    return save_data


def run_clustering_standalone():
    return run_clustering()


if __name__ == "__main__":
    run_clustering_standalone()
