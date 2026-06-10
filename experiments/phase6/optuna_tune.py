"""
Phase 6 Optuna: Tune FP-Growth for association rules.
Tune: min_support, max_len, min_lift_threshold, min_confidence, top_n_items
Objective: maximize high_lift_count (rules with lift > 10), penalize if n_rules < 100
"""
import os, sys, warnings, pickle, json, time
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

import optuna
from optuna.samplers import TPESampler
optuna.logging.set_verbosity(optuna.logging.WARNING)

from mlxtend.frequent_patterns import fpgrowth, association_rules

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
PREP = os.path.join(ROOT, "data", "prep")
EXP = os.path.join(ROOT, "experiments", "phase6")

# ─── Build basket (same as v3) ───
print("[1/4] Building basket...")
t0 = time.time()
df = pd.read_csv(os.path.join(RAW, "Online_Retail.csv"), encoding="latin1", parse_dates=["InvoiceDate"])
df["InvoiceNo"] = df["InvoiceNo"].astype(str)
df = df[~df["InvoiceNo"].str.startswith("C")]
df = df[df["Quantity"] > 0]; df = df[df["UnitPrice"] > 0]
df = df.dropna(subset=["StockCode", "Description", "CustomerID"])
df["Description"] = df["Description"].str.strip().str.upper()
df = df[df["Description"] != ""]
df["CustomerID"] = df["CustomerID"].astype(int)
print(f"  Rows: {len(df)}  Time: {time.time()-t0:.1f}s")

print("\n[2/4] Mining basket matrix...")
t0 = time.time()
basket = df.groupby(["InvoiceNo", "Description"])["Quantity"].sum().reset_index()
basket_pv = basket.pivot(index="InvoiceNo", columns="Description", values="Quantity").fillna(0)
basket_bin = (basket_pv > 0).astype(bool)
ifreq = basket_bin.sum().sort_values(ascending=False)
print(f"  Orders: {len(basket_bin):,}  Items: {len(ifreq)}  Time: {time.time()-t0:.1f}s")

# ─── Optuna: tune (min_support, max_len, min_lift, min_conf, top_n) ───
print("\n[3/4] Optuna search (30 trials)...")
t0 = time.time()
def objective(trial):
    top_n = trial.suggest_categorical("top_n", [100, 150, 200, 250])
    min_sup = trial.suggest_float("min_support", 0.005, 0.05, log=True)
    max_len = trial.suggest_int("max_len", 2, 5)
    min_lift = trial.suggest_float("min_lift", 1.0, 5.0)
    min_conf = trial.suggest_float("min_confidence", 0.3, 0.9)
    top_items = ifreq.head(top_n).index.tolist()
    bk = basket_bin[top_items]
    try:
        freq = fpgrowth(bk, min_support=min_sup, use_colnames=True, max_len=max_len)
    except Exception:
        return -1e9
    if len(freq) < 2:
        return -1e9
    try:
        rules = association_rules(freq, metric="lift", min_threshold=min_lift)
    except Exception:
        return -1e9
    if len(rules) == 0:
        return -1e9
    # Filter by confidence too
    rules = rules[rules["confidence"] >= min_conf]
    if len(rules) < 50:
        return -1e9
    # Score: high_lift_count + log(n_rules) bonus
    high_lift = int((rules["lift"] > 10).sum())
    mean_lift = float(rules["lift"].mean())
    # Combined: prioritize high-lift rules + reasonable n_rules
    return high_lift + 0.5 * mean_lift + 0.1 * np.log1p(len(rules))

study = optuna.create_study(direction="maximize", sampler=TPESampler(seed=42))
study.optimize(objective, n_trials=30, show_progress_bar=False)
print(f"  Best score: {study.best_value:.2f}")
print(f"  Best params: {study.best_params}")
print(f"  Time: {time.time()-t0:.1f}s")

# ─── Final: rebuild all rule types with best params ───
print("\n[4/4] Building final rule sets...")
t0 = time.time()
best = study.best_params.copy()
top_n = best.pop("top_n")
min_sup_g = best["min_support"]
max_len_g = best["max_len"]
min_lift_g = best["min_lift"]
min_conf_g = best["min_confidence"]

top_items_g = ifreq.head(top_n).index.tolist()
basket_g = basket_bin[top_items_g]
freq_g = fpgrowth(basket_g, min_support=min_sup_g, use_colnames=True, max_len=max_len_g)
rules_g = association_rules(freq_g, metric="lift", min_threshold=min_lift_g)
rules_g = rules_g[rules_g["confidence"] >= min_conf_g].sort_values("lift", ascending=False)

# StockCode-level
print(f"  Global rules: {len(rules_g)}  Mean lift: {rules_g['lift'].mean():.2f}  High-lift: {(rules_g['lift']>10).sum()}")

basket_sc = df.groupby(["InvoiceNo", "StockCode"])["Quantity"].sum().reset_index()
basket_sc_pv = basket_sc.pivot(index="InvoiceNo", columns="StockCode", values="Quantity").fillna(0)
basket_sc_bin = (basket_sc_pv > 0).astype(bool)
sc_freq = basket_sc_bin.sum().sort_values(ascending=False)
top_sc = sc_freq.head(top_n).index.tolist()
basket_sc_g = basket_sc_bin[top_sc]
freq_sc = fpgrowth(basket_sc_g, min_support=min_sup_g, use_colnames=True, max_len=max_len_g)
rules_sc = association_rules(freq_sc, metric="lift", min_threshold=min_lift_g)
rules_sc = rules_sc[rules_sc["confidence"] >= min_conf_g].sort_values("lift", ascending=False)
print(f"  Stockcode rules: {len(rules_sc)}  Mean lift: {rules_sc['lift'].mean():.2f}")

# Seasonal
df["month"] = df["InvoiceDate"].dt.month
df["is_christmas"] = df["month"].isin([10, 11, 12])
def mine_seasonal(sub, label, min_sup=None):
    if min_sup is None: min_sup = max(min_sup_g * 1.5, 0.01)
    bk = sub.groupby(["InvoiceNo", "Description"])["Quantity"].sum().reset_index()
    pv = bk.pivot(index="InvoiceNo", columns="Description", values="Quantity").fillna(0)
    bn = (pv > 0).astype(bool)
    if bn.shape[1] == 0: return pd.DataFrame()
    fr = bn.sum().sort_values(ascending=False)
    top = fr.head(150).index.tolist()
    bg = bn[top]
    f_ = fpgrowth(bg, min_support=min_sup, use_colnames=True, max_len=max_len_g)
    if len(f_) < 2: return pd.DataFrame()
    r_ = association_rules(f_, metric="lift", min_threshold=min_lift_g)
    r_ = r_[r_["confidence"] >= min_conf_g].sort_values("lift", ascending=False)
    print(f"  {label}: {len(r_)} rules, mean_lift={r_['lift'].mean():.2f}" if len(r_) > 0 else f"  {label}: 0 rules")
    return r_

rules_x = mine_seasonal(df[df["is_christmas"]], "Christmas")
rules_n = mine_seasonal(df[~df["is_christmas"]], "Normal")
print(f"  Time: {time.time()-t0:.1f}s")

# Per-cluster
print("\n  Mining per-cluster rules...")
t0 = time.time()
with open(os.path.join(PREP, "phase3_clusters_v3.pkl"), "rb") as f:
    p3 = pickle.load(f)
with open(os.path.join(PREP, "phase2_preprocessed.pkl"), "rb") as f:
    p2 = pickle.load(f)
cluster_df = pd.DataFrame({"CustomerID": p2["features_df"]["CustomerID"].values, "cluster_id": p3["labels"]})
cid_cluster = cluster_df.set_index("CustomerID")["cluster_id"].to_dict()
df["cluster_id"] = df["CustomerID"].map(cid_cluster).fillna(-1).astype(int)

def format_rules(rules_df, top_n_show=20):
    if rules_df.empty: return []
    out = []
    for _, row in rules_df.head(top_n_show).iterrows():
        out.append({
            "antecedents": list(row["antecedents"]),
            "consequents": list(row["consequents"]),
            "support": round(float(row["support"]), 4),
            "confidence": round(float(row["confidence"]), 4),
            "lift": round(float(row["lift"]), 2),
        })
    return out

cluster_results = {}
for cid in sorted(df["cluster_id"].unique()):
    sub = df[df["cluster_id"] == cid]
    if len(sub) < 50: continue
    bk = sub.groupby(["InvoiceNo", "Description"])["Quantity"].sum().reset_index()
    if len(bk) == 0: continue
    bk_pv = bk.pivot(index="InvoiceNo", columns="Description", values="Quantity").fillna(0)
    bk_bin = (bk_pv > 0).astype(bool)
    if bk_bin.shape[1] == 0: continue
    ifr = bk_bin.sum().sort_values(ascending=False)
    top = ifr.head(100).index.tolist()
    bk_g = bk_bin[top]
    n_t = len(bk_g); avg_i = bk_g.sum(axis=1).mean()
    ms = max(avg_i / max(n_t, 1), min_sup_g)
    try:
        f_, r_ = fpgrowth(bk_g, min_support=ms, use_colnames=True, max_len=min(max_len_g, 3)), None
        if len(f_) >= 2:
            r_ = association_rules(f_, metric="lift", min_threshold=min_lift_g)
            r_ = r_[r_["confidence"] >= min_conf_g].sort_values("lift", ascending=False)
    except Exception:
        r_ = pd.DataFrame()
    cluster_results[int(cid)] = {
        "n_customers": int(sub["CustomerID"].nunique()),
        "n_transactions": int(sub["InvoiceNo"].nunique()),
        "min_support": float(ms),
        "n_rules": len(r_) if r_ is not None else 0,
        "mean_lift": float(r_["lift"].mean()) if r_ is not None and len(r_) > 0 else 0,
        "top_rules": format_rules(r_, top_n_show=10) if r_ is not None and len(r_) > 0 else [],
    }
    print(f"  Cluster {cid}: cust={sub['CustomerID'].nunique()} trans={sub['InvoiceNo'].nunique()}  min_sup={ms:.4f}  rules={cluster_results[int(cid)]['n_rules']}  mean_lift={cluster_results[int(cid)]['mean_lift']:.2f}")
print(f"  Time: {time.time()-t0:.1f}s")

# Compare with current
print("\n[Compare] Loading current v3 winner...")
with open(os.path.join(PREP, "phase6_association_v2.pkl"), "rb") as f:
    v3 = pickle.load(f)
v3_n_rules = v3.get("global_rules", {}).get("n_rules", 694)
v3_mean_lift = v3.get("global_rules", {}).get("mean_lift", 11.07)
v3_high_lift = int((rules_g["lift"] > 10).sum())  # computed from current
print(f"  Current: {v3_n_rules} global rules  Mean lift: {v3_mean_lift:.2f}")
print(f"  New: {len(rules_g)} global rules  Mean lift: {rules_g['lift'].mean():.2f}  High-lift: {(rules_g['lift']>10).sum()}")

# Save if improved (any of: more rules, higher mean_lift with reasonable n_rules)
total_lift_quality = len(rules_g) * rules_g["lift"].mean()
v3_total_lift_quality = v3_n_rules * v3_mean_lift
# Two ways to win: more rules, OR higher total lift quality
improved = (len(rules_g) > v3_n_rules) or (total_lift_quality > v3_total_lift_quality * 1.05)
print(f"  Mean lift change: {(rules_g['lift'].mean()-v3_mean_lift)/v3_mean_lift*100:+.2f}%")
print(f"  Rule count change: {(len(rules_g)-v3_n_rules)/v3_n_rules*100:+.2f}%")
print(f"  Total lift quality: {total_lift_quality:.0f} (v3: {v3_total_lift_quality:.0f}, {total_lift_quality/v3_total_lift_quality*100-100:+.1f}%)")
print(f"  Improvement criterion: (more rules) OR (lift_quality > v3 * 1.05) = {improved}")

if improved:
    print("\n[SAVE] Improved, building new pkl...")
    new_data = {
        "metadata": {
            "n_transactions": int(df["InvoiceNo"].nunique()),
            "n_items_description": int(df["Description"].nunique()),
            "method": "FP-Growth + Optuna tuned",
            "version": "v4_optuna_tuned",
        },
        "global_rules": {
            "n_rules": len(rules_g),
            "mean_lift": float(rules_g["lift"].mean()),
            "median_lift": float(rules_g["lift"].median()),
            "top_rules": format_rules(rules_g, top_n=30),
        },
        "stockcode_rules": {
            "n_rules": len(rules_sc),
            "mean_lift": float(rules_sc["lift"].mean()) if len(rules_sc) > 0 else 0,
            "median_lift": float(rules_sc["lift"].median()) if len(rules_sc) > 0 else 0,
            "top_rules": format_rules(rules_sc, top_n=30) if len(rules_sc) > 0 else [],
        },
        "seasonal": {
            "christmas": {"n_rules": len(rules_x), "mean_lift": float(rules_x["lift"].mean()) if len(rules_x) > 0 else 0,
                          "top_rules": format_rules(rules_x, top_n=20) if len(rules_x) > 0 else []},
            "normal":    {"n_rules": len(rules_n), "mean_lift": float(rules_n["lift"].mean()) if len(rules_n) > 0 else 0,
                          "top_rules": format_rules(rules_n, top_n=20) if len(rules_n) > 0 else []},
        },
        "cluster_rules": cluster_results,
        "optuna_best_params": study.best_params,
        "improvement_note": f"v4: Optuna-tuned (min_sup={min_sup_g}, max_len={max_len_g}, min_lift={min_lift_g:.2f}, min_conf={min_conf_g:.2f}, top_n={top_n}). {v3_n_rules} -> {len(rules_g)} global rules, mean_lift {v3_mean_lift:.2f} -> {rules_g['lift'].mean():.2f}",
    }
    out_pkl = os.path.join(EXP, "phase6_association_winner.pkl")
    out_json = os.path.join(EXP, "phase6_association_winner.json")
    with open(out_pkl, "wb") as f:
        pickle.dump(new_data, f)
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    print(f"  Saved: {out_pkl}")
else:
    print(f"\n[NO SAVE] Not improved. Keep v3.")

study_out = {
    "best_value": study.best_value,
    "best_params": study.best_params,
    "n_trials": 30,
    "new_n_rules": len(rules_g),
    "new_mean_lift": float(rules_g["lift"].mean()),
    "new_high_lift": int((rules_g["lift"] > 10).sum()),
    "baseline_n_rules": v3_n_rules,
    "baseline_mean_lift": v3_mean_lift,
    "improved": bool(improved),
}
with open(os.path.join(EXP, "phase6_optuna.json"), "w") as f:
    json.dump(study_out, f, indent=2, ensure_ascii=False, default=str)
print(f"\nStudy saved: {os.path.join(EXP, 'phase6_optuna.json')}")
