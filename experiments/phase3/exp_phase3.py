"""
Phase 3 Optimization Experiments
4 directions:
  A. log1p + StandardScaler + KMeans (baseline comparison)
  B. log1p + RobustScaler + GMM soft clustering
  C. log1p + HDBSCAN
  D. log1p + MinMaxScaler + K-Means + Hopkins validation
"""
import os, sys, warnings, pickle, json, time
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

from sklearn.cluster import KMeans, MiniBatchKMeans
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler, PowerTransformer
from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
from sklearn.decomposition import PCA
from sklearn.neighbors import NearestNeighbors

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PREP = os.path.join(ROOT, "data", "prep")
EXP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.makedirs(EXP, exist_ok=True)

print("="*70)
print("Phase 3 Optimization — 4 directions")
print("="*70)

with open(os.path.join(PREP, "phase2_preprocessed.pkl"), "rb") as f:
    p2 = pickle.load(f)
features_df = p2["features_df"].copy()
print(f"Input shape: {features_df.shape}")

# Build the same RFM feature matrix used in the original
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
print(f"Feature matrix: {X_raw.shape}")

# Hopkins statistic — measures clusterability
def hopkins(X, sample_size=200, seed=42):
    rng = np.random.RandomState(seed)
    n = X.shape[0]
    s = min(sample_size, n // 2)
    idx = rng.choice(n, s, replace=False)
    sample = X[idx]
    nn = NearestNeighbors(n_neighbors=2).fit(X)
    rand_idx = rng.uniform(X.min(0), X.max(0), (s, X.shape[1]))
    d_actual, _ = nn.kneighbors(sample, n_neighbors=2)
    d_rand, _ = nn.kneighbors(rand_idx, n_neighbors=1)
    d_actual = d_actual[:, 1]  # exclude self
    H = d_actual.sum() / (d_actual.sum() + d_rand.sum())
    return float(H)

# Outlier removal (same as original)
def remove_outliers(X, k_init=5, threshold=50):
    km = KMeans(n_clusters=k_init, random_state=42, n_init=20)
    lbl = km.fit_predict(X)
    sizes = pd.Series(lbl).value_counts()
    out_ids = [c for c, s in sizes.items() if s < threshold]
    mask = ~np.isin(lbl, out_ids)
    return mask

results_all = {}

# ============== A. log1p + StandardScaler + KMeans ==============
print("\n" + "="*70)
print("A. log1p + StandardScaler + KMeans")
print("="*70)
X_log = np.log1p(X_raw)
scaler_A = StandardScaler()
X_A = scaler_A.fit_transform(X_log)
mask_A = remove_outliers(X_A, threshold=50)
XA_norm = X_A[mask_A]
H_A = hopkins(XA_norm, sample_size=300)
print(f"  Hopkins = {H_A:.4f}  (>0.5 means clusterable)")
best_A = (None, -1)
for k in range(3, 9):
    km = KMeans(n_clusters=k, random_state=42, n_init=50)
    lbl = km.fit_predict(XA_norm)
    sil = silhouette_score(XA_norm, lbl)
    db = davies_bouldin_score(XA_norm, lbl)
    ch = calinski_harabasz_score(XA_norm, lbl)
    print(f"  K={k}  Sil={sil:.4f}  DB={db:.4f}  CH={ch:.1f}")
    if sil > best_A[1]:
        best_A = (k, sil, sil, db, ch, lbl, XA_norm, mask_A)
results_all["A_log_KMeans"] = {
    "K": best_A[0], "sil": best_A[2], "db": best_A[3], "ch": best_A[4],
    "hopkins": H_A, "mask": mask_A, "X": XA_norm
}

# ============== B. log1p + GMM soft ==============
print("\n" + "="*70)
print("B. log1p + RobustScaler + GMM (soft)")
print("="*70)
X_log = np.log1p(X_raw)
scaler_B = RobustScaler()
X_B = scaler_B.fit_transform(X_log)
mask_B = remove_outliers(X_B, threshold=50)
XB_norm = X_B[mask_B]
H_B = hopkins(XB_norm, sample_size=300)
print(f"  Hopkins = {H_B:.4f}")
best_B = (None, -1)
for k in range(3, 9):
    gmm = GaussianMixture(n_components=k, random_state=42, n_init=5, covariance_type="full", max_iter=200)
    lbl = gmm.fit_predict(XB_norm)
    sil = silhouette_score(XB_norm, lbl)
    db = davies_bouldin_score(XB_norm, lbl)
    bic = gmm.bic(XB_norm)
    aic = gmm.aic(XB_norm)
    print(f"  K={k}  Sil={sil:.4f}  DB={db:.4f}  BIC={bic:.0f}  AIC={aic:.0f}")
    if sil > best_B[1]:
        best_B = (k, sil, sil, db, lbl, XB_norm, mask_B, gmm)
results_all["B_log_GMM"] = {
    "K": best_B[0], "sil": best_B[2], "db": best_B[3],
    "hopkins": H_B, "mask": mask_B, "X": XB_norm
}

# ============== C. Yeo-Johnson + KMeans (compare with log1p) ==============
print("\n" + "="*70)
print("C. Yeo-Johnson + StandardScaler + KMeans")
print("="*70)
pt = PowerTransformer(method="yeo-johnson", standardize=True)
X_C = pt.fit_transform(X_raw)
mask_C = remove_outliers(X_C, threshold=50)
XC_norm = X_C[mask_C]
H_C = hopkins(XC_norm, sample_size=300)
print(f"  Hopkins = {H_C:.4f}")
best_C = (None, -1)
for k in range(3, 9):
    km = KMeans(n_clusters=k, random_state=42, n_init=50)
    lbl = km.fit_predict(XC_norm)
    sil = silhouette_score(XC_norm, lbl)
    db = davies_bouldin_score(XC_norm, lbl)
    print(f"  K={k}  Sil={sil:.4f}  DB={db:.4f}")
    if sil > best_C[1]:
        best_C = (k, sil, sil, db, lbl, XC_norm, mask_C)
results_all["C_yeo_KMeans"] = {
    "K": best_C[0], "sil": best_C[2], "db": best_C[3],
    "hopkins": H_C, "mask": mask_C, "X": XC_norm
}

# ============== D. log1p + MinMaxScaler + MiniBatchKMeans ==============
print("\n" + "="*70)
print("D. log1p + MinMaxScaler + MiniBatchKMeans")
print("="*70)
X_log = np.log1p(X_raw)
scaler_D = MinMaxScaler()
X_D = scaler_D.fit_transform(X_log)
mask_D = remove_outliers(X_D, threshold=50)
XD_norm = X_D[mask_D]
H_D = hopkins(XD_norm, sample_size=300)
print(f"  Hopkins = {H_D:.4f}")
best_D = (None, -1)
for k in range(3, 9):
    km = MiniBatchKMeans(n_clusters=k, random_state=42, n_init=30, batch_size=256, max_iter=300)
    lbl = km.fit_predict(XD_norm)
    sil = silhouette_score(XD_norm, lbl)
    db = davies_bouldin_score(XD_norm, lbl)
    print(f"  K={k}  Sil={sil:.4f}  DB={db:.4f}")
    if sil > best_D[1]:
        best_D = (k, sil, sil, db, lbl, XD_norm, mask_D)
results_all["D_log_MBKM"] = {
    "K": best_D[0], "sil": best_D[2], "db": best_D[3],
    "hopkins": H_D, "mask": mask_D, "X": XD_norm
}

# ============== Summary ==============
print("\n" + "="*70)
print("PHASE 3 — Summary (baseline Silhouette = 0.272, DB = 1.370)")
print("="*70)
print(f"{'Method':<25} {'K':>3} {'Silhouette':>11} {'Davies-B':>10} {'Hopkins':>8} {'vs_base':>8}")
base_sil, base_db = 0.272, 1.370
for name, r in results_all.items():
    delta_sil = r["sil"] - base_sil
    delta_db = base_db - r["db"]
    winner = "BETTER" if (r["sil"] > base_sil and r["db"] < base_db) else ("partly" if r["sil"] > base_sil else "no")
    print(f"{name:<25} {r['K']:>3} {r['sil']:>11.4f} {r['db']:>10.4f} {r['hopkins']:>8.4f} {winner:>8}")

# Save comparison
with open(os.path.join(EXP, "phase3_compare.json"), "w") as f:
    json.dump({
        "baseline": {"silhouette": base_sil, "davies_bouldin": base_db, "K": 5},
        "experiments": {
            k: {"K": v["K"], "silhouette": float(v["sil"]), "davies_bouldin": float(v["db"]),
                "hopkins": float(v["hopkins"])}
            for k, v in results_all.items()
        }
    }, f, indent=2)
print(f"\nSaved -> {EXP}/phase3_compare.json")
