"""
Phase 6 Winner: lower min_support (0.008) + max_len=4
694 rules (vs 80, +767%) with mean_lift 11.07 (vs 11.31, -2.1%)
330 high-lift rules (>10) vs 80 (all)
Also adds per-cluster rules (2,314 total across 7 clusters)
"""
import os, sys, warnings, pickle, json
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

from mlxtend.frequent_patterns import fpgrowth, association_rules

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
PREP = os.path.join(ROOT, "data", "prep")
EXP = os.path.join(ROOT, "experiments", "phase6")

# Load original v2 to preserve structure
print("Loading v2 pkl...")
with open(os.path.join(PREP, "phase6_association_v2.pkl"), "rb") as f:
    v2 = pickle.load(f)
with open(os.path.join(PREP, "phase6_association_v2.json"), "r", encoding="utf-8") as f:
    v2_json = json.load(f)

# Load data
df = pd.read_csv(os.path.join(RAW, "Online_Retail.csv"), encoding="latin1", parse_dates=["InvoiceDate"])
df["InvoiceNo"] = df["InvoiceNo"].astype(str)
df = df[~df["InvoiceNo"].str.startswith("C")]
df = df[df["Quantity"] > 0]; df = df[df["UnitPrice"] > 0]
df = df.dropna(subset=["StockCode", "Description", "CustomerID"])
df["Description"] = df["Description"].str.strip().str.upper()
df = df[df["Description"] != ""]
df["CustomerID"] = df["CustomerID"].astype(int)
df["month"] = df["InvoiceDate"].dt.month
df["is_christmas"] = df["month"].isin([10, 11, 12])

# Load Phase3
with open(os.path.join(PREP, "phase3_clusters_v3.pkl"), "rb") as f:
    p3 = pickle.load(f)
with open(os.path.join(PREP, "phase2_preprocessed.pkl"), "rb") as f:
    p2 = pickle.load(f)
cluster_df = pd.DataFrame({"CustomerID": p2["features_df"]["CustomerID"].values, "cluster_id": p3["labels"]})
cid_cluster = cluster_df.set_index("CustomerID")["cluster_id"].to_dict()
df["cluster_id"] = df["CustomerID"].map(cid_cluster).fillna(-1).astype(int)

def mine_rules(basket_binary, min_support=0.008, max_len=4, min_lift=1.0):
    if basket_binary.empty or basket_binary.shape[1] == 0:
        return pd.DataFrame(), pd.DataFrame()
    freq = fpgrowth(basket_binary, min_support=min_support, use_colnames=True, max_len=max_len)
    if len(freq) < 2:
        return freq, pd.DataFrame()
    rules = association_rules(freq, metric="lift", min_threshold=min_lift)
    if len(rules) > 0:
        rules = rules.sort_values("lift", ascending=False)
    return freq, rules

def format_rules(rules_df, top_n=20):
    if rules_df.empty: return []
    out = []
    for _, row in rules_df.head(top_n).iterrows():
        out.append({
            "antecedents": list(row["antecedents"]),
            "consequents": list(row["consequents"]),
            "support": round(float(row["support"]), 4),
            "confidence": round(float(row["confidence"]), 4),
            "lift": round(float(row["lift"]), 2),
        })
    return out

# ═══ 1. Global rules (Description level) - lower threshold ═══
print("\n" + "="*70); print("1. 全局规则 (lower min_sup=0.008, max_len=4)"); print("="*70)
basket = df.groupby(["InvoiceNo", "Description"])["Quantity"].sum().reset_index()
basket_pv = basket.pivot(index="InvoiceNo", columns="Description", values="Quantity").fillna(0)
basket_bin = (basket_pv > 0).astype(bool)  # Use bool to avoid deprecation warning
ifreq = basket_bin.sum().sort_values(ascending=False)
top_items = ifreq.head(200).index.tolist()
basket_g = basket_bin[top_items]
freq_g, rules_g = mine_rules(basket_g, min_support=0.008, max_len=4, min_lift=1.0)
print(f"  Orders: {len(basket_g):,}  Items: {len(top_items)}")
print(f"  Freq itemsets: {len(freq_g)}  Rules: {len(rules_g)}")
if len(rules_g) > 0:
    print(f"  Mean lift: {rules_g['lift'].mean():.2f}  High-lift (>10): {(rules_g['lift']>10).sum()}")

# ═══ 2. StockCode-level rules ═══
print("\n" + "="*70); print("2. 编码级规则"); print("="*70)
basket_sc = df.groupby(["InvoiceNo", "StockCode"])["Quantity"].sum().reset_index()
basket_sc_pv = basket_sc.pivot(index="InvoiceNo", columns="StockCode", values="Quantity").fillna(0)
basket_sc_bin = (basket_sc_pv > 0).astype(bool)
sc_freq = basket_sc_bin.sum().sort_values(ascending=False)
top_sc = sc_freq.head(200).index.tolist()
basket_sc_g = basket_sc_bin[top_sc]
freq_sc, rules_sc = mine_rules(basket_sc_g, min_support=0.008, max_len=4, min_lift=1.0)
print(f"  Orders: {len(basket_sc_g):,}  Codes: {len(top_sc)}")
print(f"  Freq itemsets: {len(freq_sc)}  Rules: {len(rules_sc)}")
if len(rules_sc) > 0:
    print(f"  Mean lift: {rules_sc['lift'].mean():.2f}  High-lift (>10): {(rules_sc['lift']>10).sum()}")

# ═══ 3. Seasonal rules ═══
print("\n" + "="*70); print("3. 季节性规则"); print("="*70)
xmas_df = df[df["is_christmas"]]
xmas_bk = xmas_df.groupby(["InvoiceNo", "Description"])["Quantity"].sum().reset_index()
xmas_pv = xmas_bk.pivot(index="InvoiceNo", columns="Description", values="Quantity").fillna(0)
xmas_bin = (xmas_pv > 0).astype(bool)
xmas_freq = xmas_bin.sum().sort_values(ascending=False)
xmas_top = xmas_freq.head(150).index.tolist()
xmas_g = xmas_bin[xmas_top]
freq_x, rules_x = mine_rules(xmas_g, min_support=0.015, max_len=4)
print(f"  Christmas: {len(freq_x)} freq, {len(rules_x)} rules, mean_lift={rules_x['lift'].mean():.2f}" if len(rules_x) > 0 else "  Christmas: 0 rules")

norm_df = df[~df["is_christmas"]]
norm_bk = norm_df.groupby(["InvoiceNo", "Description"])["Quantity"].sum().reset_index()
norm_pv = norm_bk.pivot(index="InvoiceNo", columns="Description", values="Quantity").fillna(0)
norm_bin = (norm_pv > 0).astype(bool)
norm_freq = norm_bin.sum().sort_values(ascending=False)
norm_top = norm_freq.head(150).index.tolist()
norm_g = norm_bin[norm_top]
freq_n, rules_n = mine_rules(norm_g, min_support=0.012, max_len=4)
print(f"  Normal: {len(freq_n)} freq, {len(rules_n)} rules, mean_lift={rules_n['lift'].mean():.2f}" if len(rules_n) > 0 else "  Normal: 0 rules")

# ═══ 4. Cluster-specific rules ═══
print("\n" + "="*70); print("4. 分群规则 (Phase3)"); print("="*70)
cluster_results = {}
for cid in sorted(df["cluster_id"].unique()):
    sub = df[df["cluster_id"] == cid]
    if len(sub) < 50: continue
    bk = sub.groupby(["InvoiceNo", "Description"])["Quantity"].sum().reset_index()
    if len(bk) == 0: continue
    bk_pv = bk.pivot(index="InvoiceNo", columns="Description", values="Quantity").fillna(0)
    bk_bin = (bk_pv > 0).astype(bool)
    ifreq = bk_bin.sum().sort_values(ascending=False)
    top = ifreq.head(100).index.tolist()
    bk_g = bk_bin[top]
    n_t = len(bk_g); avg_i = bk_g.sum(axis=1).mean()
    ms = max(avg_i / max(n_t, 1), 0.01)
    f_, r_ = mine_rules(bk_g, min_support=ms, max_len=3)
    cluster_results[int(cid)] = {
        "n_customers": int(sub["CustomerID"].nunique()),
        "n_transactions": int(sub["InvoiceNo"].nunique()),
        "min_support": float(ms),
        "n_rules": len(r_),
        "mean_lift": float(r_["lift"].mean()) if len(r_) > 0 else 0,
        "top_rules": format_rules(r_, top_n=10) if len(r_) > 0 else [],
    }
    print(f"  Cluster {cid}: cust={sub['CustomerID'].nunique()} trans={sub['InvoiceNo'].nunique()}  min_sup={ms:.4f}  rules={len(r_)}  mean_lift={cluster_results[int(cid)]['mean_lift']:.2f}")

# ═══ Build new pkl (matching v2 structure) ═══
print("\n" + "="*70); print("Building winner pkl"); print("="*70)
new_data = {
    "metadata": {
        "n_transactions": int(df["InvoiceNo"].nunique()),
        "n_items_description": int(df["Description"].nunique()),
        "method": "FP-Growth + adaptive min_support + cluster-specific",
        "version": "v3_more_rules_cluster_aware",
    },
    "global_rules": {
        "n_rules": len(rules_g),
        "mean_lift": float(rules_g["lift"].mean()) if len(rules_g) > 0 else 0,
        "median_lift": float(rules_g["lift"].median()) if len(rules_g) > 0 else 0,
        "top_rules": format_rules(rules_g, top_n=30),
    },
    "stockcode_rules": {
        "n_rules": len(rules_sc),
        "mean_lift": float(rules_sc["lift"].mean()) if len(rules_sc) > 0 else 0,
        "median_lift": float(rules_sc["lift"].median()) if len(rules_sc) > 0 else 0,
        "top_rules": format_rules(rules_sc, top_n=30),
    },
    "seasonal": {
        "christmas": {"n_rules": len(rules_x), "mean_lift": float(rules_x["lift"].mean()) if len(rules_x) > 0 else 0,
                      "top_rules": format_rules(rules_x, top_n=20) if len(rules_x) > 0 else []},
        "normal":    {"n_rules": len(rules_n), "mean_lift": float(rules_n["lift"].mean()) if len(rules_n) > 0 else 0,
                      "top_rules": format_rules(rules_n, top_n=20) if len(rules_n) > 0 else []},
    },
    "cluster_rules": cluster_results,
    "improvement_note": f"v3: lower min_support 0.015->0.008, max_len 3->4 -> {len(rules_g)} global rules ({len(rules_g)/80*100:.0f}% more, mean_lift={rules_g['lift'].mean():.2f}). Added per-cluster rules: {sum(c['n_rules'] for c in cluster_results.values())} total across {len(cluster_results)} clusters.",
}

# Save new pkl
out_pkl = os.path.join(EXP, "phase6_association_winner.pkl")
with open(out_pkl, "wb") as f:
    pickle.dump(new_data, f)
out_json = os.path.join(EXP, "phase6_association_winner.json")
with open(out_json, "w", encoding="utf-8") as f:
    json.dump(new_data, f, ensure_ascii=False, indent=2)

print(f"\nWinner pkl saved: {out_pkl}")
print(f"  Global rules: {len(rules_g)} (vs v2 80, +{len(rules_g)-80})")
print(f"  Mean lift: {new_data['global_rules']['mean_lift']:.2f} (vs v2 11.31)")
print(f"  Stockcode rules: {len(rules_sc)} (vs v2 152)")
print(f"  Cluster rules: {sum(c['n_rules'] for c in cluster_results.values())} (NEW)")
print(f"  Christmas rules: {len(rules_x)} (vs v2 56)")
print(f"  Normal rules: {len(rules_n)} (vs v2 116)")
