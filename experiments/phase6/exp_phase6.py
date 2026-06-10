"""
Phase 6 Optimization — 4 directions
A. Adaptive min_support (Hidayat 2021)
B. fpmax (closed maximal itemsets - compact)
C. Lower min_support + max_len=4 (find more rules)
D. Multi-min_support per category (more granular)
"""
import os, sys, warnings, pickle, json, time
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

from mlxtend.frequent_patterns import fpgrowth, fpmax, association_rules

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
EXP = os.path.join(ROOT, "experiments", "phase6")

# Load and clean
print("Loading data...")
df = pd.read_csv(os.path.join(RAW, "Online_Retail.csv"), encoding="latin1", parse_dates=["InvoiceDate"])
df["InvoiceNo"] = df["InvoiceNo"].astype(str)
df = df[~df["InvoiceNo"].str.startswith("C")]
df = df[df["Quantity"] > 0]; df = df[df["UnitPrice"] > 0]
df = df.dropna(subset=["StockCode", "Description", "CustomerID"])
df["Description"] = df["Description"].str.strip().str.upper()
df = df[df["Description"] != ""]
df["CustomerID"] = df["CustomerID"].astype(int)
print(f"  Cleaned: {len(df):,}  Invoices: {df['InvoiceNo'].nunique():,}  Items: {df['Description'].nunique():,}")

# Build basket
basket = df.groupby(["InvoiceNo", "Description"])["Quantity"].sum().reset_index()
basket_pivot = basket.pivot(index="InvoiceNo", columns="Description", values="Quantity").fillna(0)
basket_binary = (basket_pivot > 0).astype(int)
item_freq = basket_binary.sum().sort_values(ascending=False)
top_items = item_freq.head(200).index.tolist()
basket_global = basket_binary[top_items]
print(f"  Top-200 basket: {basket_global.shape}")

# ═══ A. Adaptive min_support ═══
print("\n" + "="*70); print("A. Adaptive min_support (Hidayat 2021)"); print("="*70)
n_trans = len(basket_global)
avg_items = basket_global.sum(axis=1).mean()
total_utility = item_freq.sum()
adaptive_min_sup = avg_items / n_trans
print(f"  Adaptive threshold: {adaptive_min_sup:.4f} (avg_items/trans={avg_items:.2f})")
t0 = time.time()
freq_a = fpgrowth(basket_global, min_support=adaptive_min_sup, use_colnames=True, max_len=3)
t_a = time.time() - t0
rules_a = association_rules(freq_a, metric="lift", min_threshold=1.0) if len(freq_a) > 1 else pd.DataFrame()
if len(rules_a) > 0:
    rules_a = rules_a.sort_values("lift", ascending=False)
mean_lift_a = float(rules_a["lift"].mean()) if len(rules_a) > 0 else 0
print(f"  min_sup={adaptive_min_sup:.4f}  freq={len(freq_a)}  rules={len(rules_a)}  mean_lift={mean_lift_a:.2f}  time={t_a:.1f}s")

# Also try 3 different adaptive levels
for level in [0.5, 0.25, 0.1]:
    ms = max(adaptive_min_sup * level, 0.003)
    freq_ = fpgrowth(basket_global, min_support=ms, use_colnames=True, max_len=3)
    rules_ = association_rules(freq_, metric="lift", min_threshold=1.0) if len(freq_) > 1 else pd.DataFrame()
    n_rules = len(rules_)
    mean_l = float(rules_["lift"].mean()) if n_rules > 0 else 0
    print(f"  level={level}: min_sup={ms:.4f}  freq={len(freq_)}  rules={n_rules}  mean_lift={mean_l:.2f}")

# ═══ B. fpmax (closed maximal itemsets) ═══
print("\n" + "="*70); print("B. fpmax (closed maximal itemsets)"); print("="*70)
t0 = time.time()
freq_b = fpmax(basket_global, min_support=0.015, use_colnames=True, max_len=4)
t_b = time.time() - t0
# fpmax only returns MAXIMAL itemsets. Use fpgrowth instead to get all itemsets for rule mining
print(f"  fpmax: {len(freq_b)} maximal itemsets  time={t_b:.1f}s")
# Compare to fpgrowth at same params
t0 = time.time()
freq_b_fpg = fpgrowth(basket_global, min_support=0.015, use_colnames=True, max_len=4)
t_b_fpg = time.time() - t0
rules_b = association_rules(freq_b_fpg, metric="lift", min_threshold=1.0) if len(freq_b_fpg) > 1 else pd.DataFrame()
if len(rules_b) > 0:
    rules_b = rules_b.sort_values("lift", ascending=False)
mean_lift_b = float(rules_b["lift"].mean()) if len(rules_b) > 0 else 0
print(f"  fpgrowth (same params): {len(freq_b_fpg)} itemsets, {len(rules_b)} rules, mean_lift={mean_lift_b:.2f}  time={t_b_fpg:.1f}s")
print(f"  → fpmax is {t_b_fpg/t_b:.1f}x faster but doesn't generate superset rules")

# ═══ C. Lower min_support + max_len=4 ═══
print("\n" + "="*70); print("C. Lower min_support + max_len=4"); print("="*70)
t0 = time.time()
freq_c = fpgrowth(basket_global, min_support=0.008, use_colnames=True, max_len=4)
t_c = time.time() - t0
rules_c = association_rules(freq_c, metric="lift", min_threshold=1.0) if len(freq_c) > 1 else pd.DataFrame()
if len(rules_c) > 0:
    rules_c = rules_c.sort_values("lift", ascending=False)
mean_lift_c = float(rules_c["lift"].mean()) if len(rules_c) > 0 else 0
n_high_lift_c = int((rules_c["lift"] > 10).sum()) if len(rules_c) > 0 else 0
print(f"  min_sup=0.008  max_len=4  freq={len(freq_c)}  rules={len(rules_c)}  mean_lift={mean_lift_c:.2f}  high_lift(>10)={n_high_lift_c}  time={t_c:.1f}s")

# ═══ D. Multi-min_support per category (cluster-aware) ═══
print("\n" + "="*70); print("D. Cluster-specific (Phase3 clusters) + adaptive min_sup"); print("="*70)
# Load Phase3 clusters
try:
    with open(os.path.join(ROOT, "data", "prep", "phase3_clusters_v3.pkl"), "rb") as f:
        p3 = pickle.load(f)
    with open(os.path.join(ROOT, "data", "prep", "phase2_preprocessed.pkl"), "rb") as f:
        p2 = pickle.load(f)
    cluster_df = pd.DataFrame({"CustomerID": p2["features_df"]["CustomerID"].values, "cluster_id": p3["labels"]})
    # Per-cluster baskets
    cid_cluster = cluster_df.set_index("CustomerID")["cluster_id"].to_dict()
    df["cluster_id"] = df["CustomerID"].map(cid_cluster).fillna(-1).astype(int)
    cluster_results = {}
    for cid in sorted(df["cluster_id"].unique()):
        sub = df[df["cluster_id"] == cid]
        if len(sub) < 50: continue
        bk = sub.groupby(["InvoiceNo", "Description"])["Quantity"].sum().reset_index()
        if len(bk) == 0: continue
        bk_pv = bk.pivot(index="InvoiceNo", columns="Description", values="Quantity").fillna(0)
        bk_bin = (bk_pv > 0).astype(int)
        ifreq = bk_bin.sum().sort_values(ascending=False)
        top = ifreq.head(100).index.tolist()
        bk_g = bk_bin[top]
        # Adaptive min_sup per cluster
        n_t = len(bk_g)
        avg_i = bk_g.sum(axis=1).mean()
        ms = max(avg_i / n_t, 0.01) if n_t > 0 else 0.01
        f_ = fpgrowth(bk_g, min_support=ms, use_colnames=True, max_len=3)
        r_ = association_rules(f_, metric="lift", min_threshold=1.0) if len(f_) > 1 else pd.DataFrame()
        n_r = len(r_)
        m_l = float(r_["lift"].mean()) if n_r > 0 else 0
        cluster_results[int(cid)] = {"n_customers": int(sub["CustomerID"].nunique()),
                                      "n_transactions": int(sub["InvoiceNo"].nunique()),
                                      "min_support": float(ms),
                                      "n_rules": n_r, "mean_lift": m_l}
        print(f"  Cluster {cid}: cust={sub['CustomerID'].nunique()} trans={sub['InvoiceNo'].nunique()}  min_sup={ms:.4f}  rules={n_r}  mean_lift={m_l:.2f}")
except Exception as e:
    print(f"  Failed: {e}")
    cluster_results = {}

# ═══ Summary ═══
print("\n" + "="*70)
print("PHASE 6 Summary (baseline: 80 rules global, 152 stockcode, mean_lift=11.31)")
print("="*70)
print(f"{'Method':<30} {'Rules':>6} {'MeanLift':>10} {'HighLift>10':>12}")
print(f"  {'A_adaptive (auto)':<28} {len(rules_a):>6} {mean_lift_a:>10.2f}")
print(f"  {'B_fpmax (closed)':<28} {len(rules_b):>6} {mean_lift_b:>10.2f}")
print(f"  {'C_low_sup+max4':<28} {len(rules_c):>6} {mean_lift_c:>10.2f} {n_high_lift_c:>12}")
total_cluster_rules = sum(c["n_rules"] for c in cluster_results.values())
print(f"  {'D_cluster_specific':<28} {total_cluster_rules:>6} (sum of {len(cluster_results)} clusters)")

# Save comparison
with open(os.path.join(EXP, "phase6_compare.json"), "w") as f:
    json.dump({
        "baseline": {"global_rules": 80, "stockcode_rules": 152, "mean_lift": 11.31},
        "A_adaptive": {"rules": len(rules_a), "mean_lift": mean_lift_a, "time_s": t_a},
        "B_fpmax": {"rules": len(rules_b), "mean_lift": mean_lift_b, "time_s": t_b},
        "C_low_sup_max4": {"rules": len(rules_c), "mean_lift": mean_lift_c, "high_lift_10": n_high_lift_c, "time_s": t_c},
        "D_cluster": cluster_results
    }, f, indent=2)
print(f"\nSaved -> {EXP}/phase6_compare.json")
