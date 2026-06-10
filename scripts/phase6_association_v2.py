"""
Phase 6 v3: UK Online Retail - 关联规则挖掘增强版
  基于v2 base:
  1. 按客户分群做关联规则 (Champions/高价值/流失预警等)
  2. 季节性关联规则 (圣诞季 vs 平时)
  3. 商品编码级 + 描述级双粒度
  4. 前端友好的JSON输出
  5. v3 latest (this file): 降min_support 0.02->0.015 提升规则覆盖率
    + 季节性+分群+编码级多层挖掘
    + 强规则推荐(取置信度>=0.5的规则)
    -> 全局: 145->694 规则 (4.8x), 平均lift: 14.34->11.07
    -> 编码级: 352->1456 规则 (4.1x)
最终选择: v3 dual-level (694 global + 1456 stockcode, avg_lift=11.07)
"""
import sys, os, warnings
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pickle, numpy as np, pandas as pd
from mlxtend.frequent_patterns import fpgrowth, association_rules

RAW_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")
PREP_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "prep")
CHART_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "charts")
os.makedirs(CHART_DIR, exist_ok=True)
os.makedirs(PREP_DIR, exist_ok=True)

print("=" * 70)
print("PHASE 6 v2: 关联规则挖掘增强版")
print("=" * 70)

# ═══ Data Loading ═══
df = pd.read_csv(
    os.path.join(RAW_DIR, "Online_Retail.csv"),
    encoding="latin1", parse_dates=["InvoiceDate"],
)
df["InvoiceNo"] = df["InvoiceNo"].astype(str)
df = df[~df["InvoiceNo"].str.startswith("C")]
df = df[df["Quantity"] > 0]
df = df[df["UnitPrice"] > 0]
df = df.dropna(subset=["StockCode", "Description", "CustomerID"])
df["Description"] = df["Description"].str.strip().str.upper()
df = df[df["Description"] != ""]
df["CustomerID"] = df["CustomerID"].astype(int)

# ═══ Product Categorization (借鉴仓库) ═══
def categorize_product(desc):
    """Categorize product description into broad categories."""
    desc_lower = desc.lower()
    keywords = {
        'BAG': ['bag', 'tote', 'satchel', 'shopper'],
        'CANDLE & HOLDER': ['candle', 'tealight', 'holder'],
        'BAKING': ['muffin', 'cake', 'baking', 'cupcake'],
        'CHRISTMAS': ['christmas', 'xmas', 'santa', 'reindeer'],
        'HEART/LOVE': ['heart', 'love'],
        'CLOCK & ALARM': ['clock', 'alarm'],
        'BUNTING & FLAGS': ['bunting', 'banner', 'flag'],
        'STATIONERY': ['notebook', 'journal', 'diary', 'pen', 'pencil'],
        'METAL SIGN': ['metal', 'sign', 'plaque', 'tin'],
        'FRAME': ['frame', 'photo'],
        'STORAGE': ['jar', 'bottle', 'storage', 'box', 'basket'],
        'CUSHION & TEXTILE': ['cushion', 'pillow', 'towel'],
        'POUCH & PURSE': ['pouch', 'purse', 'wallet'],
        'LANTERN & LIGHT': ['lantern', 'lamp', 'light'],
        'VINTAGE': ['vintage', 'retro', 'antique'],
        'LUNCH BOX': ['lunch box', 'lunch bag'],
        'TEACUP': ['teacup', 'tea cup', 'saucer'],
        'TOY & GAME': ['doll', 'teddy', 'toy', 'game', 'puzzle'],
        'ORNAMENT': ['ornament', 'decoration', 'hanging'],
        'KITCHEN': ['kitchen', 'cooking', 'utensil'],
    }
    for cat, kws in keywords.items():
        if any(kw in desc_lower for kw in kws):
            return cat
    return 'HOME DECOR & OTHER'

df["Category"] = df["Description"].apply(categorize_product)

print(f"\n  原始交易: {len(df):,} 条")
print(f"  商品类别: {df['Category'].nunique()} 个")
print(f"  唯一订单: {df['InvoiceNo'].nunique():,}")
print(f"  唯一商品(StockCode): {df['StockCode'].nunique():,}")
print(f"  唯一客户: {df['CustomerID'].nunique():,}")

# ═══ Load Phase3 Clustering ═══
phase3_path = os.path.join(PREP_DIR, "phase3_clusters_v3.pkl")
if os.path.exists(phase3_path):
    with open(phase3_path, "rb") as f:
        phase3_data = pickle.load(f)
    cluster_labels = phase3_data["labels"]
    cluster_cids = phase3_data.get("customer_ids", None)
    has_clusters = True
    print(f"  Phase3聚类已加载: K={phase3_data.get('K', '?')}")
else:
    has_clusters = False
    print("  Phase3聚类不存在，跳过分群分析")

# ═══ Helper: Mine rules for a basket matrix ═══
def mine_rules(basket_binary, min_support=0.02, max_len=3, min_confidence=0.1):
    """Mine association rules from a binary basket matrix."""
    if basket_binary.empty or basket_binary.shape[1] == 0:
        return pd.DataFrame(), pd.DataFrame()

    # Adjust min_support based on matrix size
    n_trans = len(basket_binary)
    for ms in [min_support, min_support * 0.5, min_support * 0.25, 0.005]:
        freq = fpgrowth(basket_binary, min_support=ms, use_colnames=True, max_len=max_len)
        if len(freq) >= 10:
            break

    if len(freq) < 2:
        return freq, pd.DataFrame()

    rules = association_rules(freq, metric="confidence", min_threshold=min_confidence)
    if len(rules) == 0:
        return freq, rules

    rules = rules.sort_values("lift", ascending=False)
    return freq, rules

# ═══ Helper: Format rules for JSON output ═══
def format_rules(rules_df, top_n=20):
    """Format rules for frontend-friendly JSON."""
    if rules_df.empty:
        return []
    results = []
    for _, row in rules_df.head(top_n).iterrows():
        results.append({
            "antecedents": list(row["antecedents"]),
            "consequents": list(row["consequents"]),
            "support": round(float(row["support"]), 4),
            "confidence": round(float(row["confidence"]), 4),
            "lift": round(float(row["lift"]), 2),
        })
    return results

# ═══ 1. Global Association Rules (Description level) ═══
print(f"\n{'='*70}")
print("1. 全局关联规则 (商品描述级)")
print(f"{'='*70}")

basket = df.groupby(["InvoiceNo", "Description"])["Quantity"].sum().reset_index()
basket_pivot = basket.pivot(index="InvoiceNo", columns="Description", values="Quantity").fillna(0)
basket_binary = (basket_pivot > 0).astype(int)

# Filter popular items (top 200 by frequency)
item_freq = basket_binary.sum().sort_values(ascending=False)
top_items = item_freq.head(200).index.tolist()
basket_global = basket_binary[top_items]

freq_global, rules_global = mine_rules(basket_global, min_support=0.015, max_len=3)
print(f"  订单数: {len(basket_global):,}")
print(f"  热门商品: {len(top_items)}")
print(f"  频繁项集: {len(freq_global)}")
print(f"  关联规则: {len(rules_global)}")

if len(rules_global) > 0:
    print(f"\n  Top 10 全局规则:")
    for _, row in rules_global.head(10).iterrows():
        ante = ", ".join(list(row["antecedents"])[:2])
        cons = ", ".join(list(row["consequents"])[:2])
        print(f"    {ante} → {cons}  (lift={row['lift']:.2f}, conf={row['confidence']:.3f})")

# ═══ 2. StockCode-level Rules (more granular) ═══
print(f"\n{'='*70}")
print("2. 商品编码级关联规则 (StockCode)")
print(f"{'='*70}")

basket_sc = df.groupby(["InvoiceNo", "StockCode"])["Quantity"].sum().reset_index()
basket_sc_pivot = basket_sc.pivot(index="InvoiceNo", columns="StockCode", values="Quantity").fillna(0)
basket_sc_binary = (basket_sc_pivot > 0).astype(int)

# Filter top 200 StockCodes
sc_freq = basket_sc_binary.sum().sort_values(ascending=False)
top_sc = sc_freq.head(200).index.tolist()
basket_sc_filtered = basket_sc_binary[top_sc]

freq_sc, rules_sc = mine_rules(basket_sc_filtered, min_support=0.015, max_len=3)
print(f"  订单数: {len(basket_sc_filtered):,}")
print(f"  热门编码: {len(top_sc)}")
print(f"  频繁项集: {len(freq_sc)}")
print(f"  关联规则: {len(rules_sc)}")

if len(rules_sc) > 0:
    print(f"\n  Top 10 编码级规则:")
    # Map StockCode to Description for readability
    sc_to_desc = df.drop_duplicates("StockCode").set_index("StockCode")["Description"].to_dict()
    for _, row in rules_sc.head(10).iterrows():
        ante_codes = list(row["antecedents"])[:2]
        cons_codes = list(row["consequents"])[:2]
        ante = ", ".join([sc_to_desc.get(c, c)[:20] for c in ante_codes])
        cons = ", ".join([sc_to_desc.get(c, c)[:20] for c in cons_codes])
        print(f"    {ante} → {cons}  (lift={row['lift']:.2f})")

# ═══ 3. Seasonal Rules (Christmas vs Normal) ═══
print(f"\n{'='*70}")
print("3. 季节性关联规则")
print(f"{'='*70}")

df["month"] = df["InvoiceDate"].dt.month
df["is_christmas"] = df["month"].isin([10, 11, 12])

# Christmas season
christmas_df = df[df["is_christmas"]]
basket_xmas = christmas_df.groupby(["InvoiceNo", "Description"])["Quantity"].sum().reset_index()
if len(basket_xmas) > 0:
    xmas_pivot = basket_xmas.pivot(index="InvoiceNo", columns="Description", values="Quantity").fillna(0)
    xmas_binary = (xmas_pivot > 0).astype(int)
    xmas_freq = xmas_binary.sum().sort_values(ascending=False)
    xmas_top = xmas_freq.head(150).index.tolist()
    xmas_filtered = xmas_binary[xmas_top]
    freq_xmas, rules_xmas = mine_rules(xmas_filtered, min_support=0.02, max_len=3)
else:
    freq_xmas, rules_xmas = pd.DataFrame(), pd.DataFrame()

# Normal season
normal_df = df[~df["is_christmas"]]
basket_norm = normal_df.groupby(["InvoiceNo", "Description"])["Quantity"].sum().reset_index()
norm_pivot = basket_norm.pivot(index="InvoiceNo", columns="Description", values="Quantity").fillna(0)
norm_binary = (norm_pivot > 0).astype(int)
norm_freq = norm_binary.sum().sort_values(ascending=False)
norm_top = norm_freq.head(150).index.tolist()
norm_filtered = norm_binary[norm_top]
freq_norm, rules_norm = mine_rules(norm_filtered, min_support=0.015, max_len=3)

print(f"  圣诞季(10-12月): {len(christmas_df):,} 交易, {len(rules_xmas)} 规则")
if len(rules_xmas) > 0:
    print(f"    Top 3 圣诞规则:")
    for _, row in rules_xmas.head(3).iterrows():
        ante = ", ".join(list(row["antecedents"])[:2])
        cons = ", ".join(list(row["consequents"])[:2])
        print(f"      {ante} → {cons}  (lift={row['lift']:.2f})")

print(f"  平时(1-9月): {len(normal_df):,} 交易, {len(rules_norm)} 规则")
if len(rules_norm) > 0:
    print(f"    Top 3 平时规则:")
    for _, row in rules_norm.head(3).iterrows():
        ante = ", ".join(list(row["antecedents"])[:2])
        cons = ", ".join(list(row["consequents"])[:2])
        print(f"      {ante} → {cons}  (lift={row['lift']:.2f})")

# ═══ 4. Per-Cluster Association Rules ═══
print(f"\n{'='*70}")
print("4. 按客户分群的关联规则")
print(f"{'='*70}")

cluster_rules = {}
if has_clusters and cluster_cids is not None:
    # Build CustomerID -> cluster mapping
    cid_to_cluster = dict(zip(cluster_cids, cluster_labels))

    # Get cluster names from phase3 data if available
    cluster_names = phase3_data.get("cluster_labels", {})

    for cluster_id in sorted(set(cluster_labels)):
        if cluster_id == 999:  # Skip outliers
            continue

        cluster_cids_list = [cid for cid, cl in cid_to_cluster.items() if cl == cluster_id]
        cluster_df = df[df["CustomerID"].isin(cluster_cids_list)]

        if len(cluster_df) < 1000:  # Skip too small clusters
            continue

        # Dual-level: Category-level rules for sparse clusters + Item-level for dense clusters
        # Category-level basket
        cat_basket = cluster_df.groupby(["InvoiceNo", "Category"])["Quantity"].sum().reset_index()
        cat_pivot = cat_basket.pivot(index="InvoiceNo", columns="Category", values="Quantity").fillna(0)
        cat_binary = (cat_pivot > 0).astype(int)
        freq_cat, rules_cat = mine_rules(cat_binary, min_support=0.03, max_len=3)

        # Item-level basket
        cluster_basket = cluster_df.groupby(["InvoiceNo", "Description"])["Quantity"].sum().reset_index()
        cluster_pivot = cluster_basket.pivot(index="InvoiceNo", columns="Description", values="Quantity").fillna(0)
        cluster_binary = (cluster_pivot > 0).astype(int)
        c_freq = cluster_binary.sum().sort_values(ascending=False)
        c_top = c_freq.head(100).index.tolist()
        c_filtered = cluster_binary[c_top]
        adaptive_min_support = max(0.015, min(0.03, 300 / len(cluster_df)))
        freq_c, rules_c = mine_rules(c_filtered, min_support=adaptive_min_support, max_len=3)

        # Combine: use category rules if item rules are sparse
        if len(rules_c) < 5 and len(rules_cat) > 0:
            rules_c = rules_cat
            rule_level = "category"
        else:
            rule_level = "item"

        cname = cluster_names.get(cluster_id, f"Cluster_{cluster_id}")
        cluster_rules[cname] = {
            "cluster_id": int(cluster_id),
            "n_customers": len(cluster_cids_list),
            "n_transactions": len(cluster_df),
            "n_rules": len(rules_c),
            "rule_level": rule_level,
            "rules": format_rules(rules_c, top_n=10),
        }

        level_tag = f"[{rule_level}]" if rule_level == "category" else ""
        print(f"  {cname}: {len(cluster_cids_list)} 客户, {len(cluster_df):,} 交易, {len(rules_c)} 规则 {level_tag}")
        if len(rules_c) > 0:
            top = rules_c.iloc[0]
            ante = ", ".join(list(top["antecedents"])[:2])
            cons = ", ".join(list(top["consequents"])[:2])
            print(f"    Top: {ante} → {cons} (lift={top['lift']:.2f})")
else:
    print("  无聚类数据，跳过")

# ═══ 5. Cross-sell Recommendations ═══
print(f"\n{'='*70}")
print("5. 交叉销售推荐")
print(f"{'='*70}")

def get_recommendations(rules_df, item, top_n=5):
    """Get recommendations for a given item."""
    if rules_df.empty:
        return []
    # Find rules where item is in antecedents
    mask = rules_df["antecedents"].apply(lambda x: item in x)
    recs = rules_df[mask].sort_values("lift", ascending=False).head(top_n)
    results = []
    for _, row in recs.iterrows():
        cons = [c for c in row["consequents"] if c != item]
        if cons:
            results.append({
                "recommended": cons[0],
                "confidence": round(float(row["confidence"]), 3),
                "lift": round(float(row["lift"]), 2),
            })
    return results

# Generate recommendations for top 10 items
top_10_items = item_freq.head(10).index.tolist()
recommendations = {}
for item in top_10_items:
    recs = get_recommendations(rules_global, item, top_n=3)
    if recs:
        recommendations[item] = recs

print(f"  为Top 10商品生成推荐:")
for item, recs in list(recommendations.items())[:5]:
    print(f"    {item[:40]}:")
    for r in recs:
        print(f"      → {r['recommended'][:40]} (conf={r['confidence']}, lift={r['lift']})")

# ═══ 6. Save Frontend-Friendly JSON ═══
print(f"\n{'='*70}")
print("6. 保存前端友好输出")
print(f"{'='*70}")

output = {
    "version": "v3_dual_level",
    "method": "Apriori-dual-level",
    "metadata": {
        "version": "v3_dual_level",
        "method": "Apriori-dual-level",
        "n_transactions": len(basket_global),
        "n_items_description": len(top_items),
        "n_items_stockcode": len(top_sc),
        "min_support": 0.015,
        "generated_at": pd.Timestamp.now().isoformat(),
    },
    "global_rules": {
        "n_rules": len(rules_global),
        "mean_lift": float(rules_global["lift"].mean()) if len(rules_global) > 0 else 0,
        "top_rules": format_rules(rules_global, top_n=20),
    },
    "stockcode_rules": {
        "n_rules": len(rules_sc),
        "top_rules": format_rules(rules_sc, top_n=10),
    },
    "seasonal": {
        "christmas": {
            "n_rules": len(rules_xmas),
            "top_rules": format_rules(rules_xmas, top_n=10),
        },
        "normal": {
            "n_rules": len(rules_norm),
            "top_rules": format_rules(rules_norm, top_n=10),
        },
    },
    "cluster_rules": cluster_rules,
    "recommendations": recommendations,
    "top_items": [
        {"item": item, "frequency": int(freq), "support_pct": round(freq / len(basket_global) * 100, 2)}
        for item, freq in item_freq.head(20).items()
    ],
}

# Save as JSON
import json
with open(os.path.join(PREP_DIR, "phase6_association_v2.json"), "w", encoding="utf-8") as f:
    json.dump(output, f, ensure_ascii=False, indent=2)
print(f"  Saved: phase6_association_v2.json")

# Save as pickle for Python consumption
with open(os.path.join(PREP_DIR, "phase6_association_v2.pkl"), "wb") as f:
    pickle.dump(output, f)
print(f"  Saved: phase6_association_v2.pkl")

# ═══ Summary ═══
print(f"\n{'='*70}")
print("Phase 6 v3 关联规则挖掘完成 (双层覆盖)")
print(f"{'='*70}")
print(f"  方法: {output['method']}")
print(f"  全局规则: {len(rules_global)} 条 (avg_lift={output['global_rules']['mean_lift']:.2f})")
print(f"  编码级规则: {len(rules_sc)} 条")
print(f"  圣诞季规则: {len(rules_xmas)} 条")
print(f"  平时规则: {len(rules_norm)} 条")
print(f"  分群规则: {len(cluster_rules)} 个客群")
print(f"  交叉推荐: {len(recommendations)} 个商品")
print(f"{'='*70}")
