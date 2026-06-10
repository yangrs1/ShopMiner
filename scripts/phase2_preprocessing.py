"""
ShopMiner — Phase 2: 数据预处理与特征工程
读取 Online_Retail.csv → 清洗 → RFM计算 → 22维行为特征 → 标准化
输出 phase2_preprocessed.pkl (供 Phase3~6 使用)
"""
import sys, os, pickle
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

PREP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "prep")
RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "raw")
os.makedirs(PREP_DIR, exist_ok=True)


def run_preprocessing():
    print("=" * 60)
    print("  Phase 2: 数据预处理与特征工程")
    print("=" * 60)

    csv_path = os.path.join(RAW_DIR, "Online_Retail.csv")
    if not os.path.exists(csv_path):
        print(f"  ERROR: 未找到 {csv_path}")
        return

    # ─── 1. 加载数据 ───
    print("\n[1/6] 加载原始数据...")
    df = pd.read_csv(csv_path, encoding="latin-1")
    print(f"  原始记录: {len(df):,}")

    # ─── 2. 数据清洗 ───
    print("\n[2/6] 数据清洗...")
    df = df.dropna(subset=["CustomerID", "InvoiceNo", "StockCode", "Description"])
    df = df[~df["InvoiceNo"].astype(str).str.startswith("C")]
    df["CustomerID"] = df["CustomerID"].astype(int)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["UnitPrice"] = df["UnitPrice"].astype(float)
    df["Quantity"] = df["Quantity"].astype(int)
    df = df[(df["Quantity"] > 0) & (df["UnitPrice"] > 0)]
    df["LineTotal"] = df["Quantity"] * df["UnitPrice"]
    df["InvoiceDateOnly"] = df["InvoiceDate"].dt.date
    print(f"  清洗后记录: {len(df):,}")

    # ─── 3. 客户维度特征 ───
    print("\n[3/6] 构建客户特征...")
    today = df["InvoiceDateOnly"].max()

    cust = df.groupby("CustomerID").agg(
        total_items=("Quantity", "sum"),
        total_spent=("LineTotal", "sum"),
        total_orders=("InvoiceNo", "nunique"),
        unique_products=("StockCode", "nunique"),
        avg_item_price=("UnitPrice", "mean"),
        price_std=("UnitPrice", "std"),
        price_min=("UnitPrice", "min"),
        price_max=("UnitPrice", "max"),
        first_purchase=("InvoiceDateOnly", "min"),
        last_purchase=("InvoiceDateOnly", "max"),
        avg_purchase_hour=("InvoiceDate", lambda x: x.dt.hour.mean()),
        hour_std=("InvoiceDate", lambda x: x.dt.hour.std()),
        weekend_pct=("InvoiceDate", lambda x: x.dt.dayofweek.isin([5, 6]).mean()),
        nights_pct=("InvoiceDate", lambda x: (x.dt.hour < 6).mean()),
    ).reset_index()

    cust["purchase_span_days"] = (pd.to_datetime(cust["last_purchase"]) - pd.to_datetime(cust["first_purchase"])).dt.days
    cust["recency_days"] = (pd.Timestamp(today) - pd.to_datetime(cust["last_purchase"])).dt.days
    cust["avg_items_per_order"] = cust["total_items"] / cust["total_orders"]
    cust["avg_spend_per_order"] = cust["total_spent"] / cust["total_orders"]

    cust["price_p25"] = df.groupby("CustomerID")["UnitPrice"].quantile(0.25).values
    cust["price_p75"] = df.groupby("CustomerID")["UnitPrice"].quantile(0.75).values
    cust["price_range"] = cust["price_max"] - cust["price_min"]
    cust["price_cv"] = cust["price_std"] / cust["avg_item_price"]

    cust["is_night"] = cust["nights_pct"]
    cust["is_weekday"] = 1 - cust["weekend_pct"]
    cust["weekend_ratio"] = cust["weekend_pct"]

    avg_purchase_interval = []
    for cid in cust["CustomerID"]:
        dates = df[df["CustomerID"] == cid]["InvoiceDateOnly"].unique()
        dates = sorted(dates)
        if len(dates) > 1:
            intervals = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
            avg_purchase_interval.append(np.mean(intervals))
        else:
            avg_purchase_interval.append(0)
    cust["avg_purchase_interval"] = avg_purchase_interval

    cust["avg_purchase_hour"] = cust["avg_purchase_hour"].fillna(12)
    cust["hour_std"] = cust["hour_std"].fillna(0)

    # ─── 4. 流失标签 ───
    print("\n[4/6] 计算流失标签...")
    quantiles = cust["recency_days"].quantile([0.2, 0.4, 0.6, 0.8])
    def label_prob(r):
        if r <= quantiles.iloc[0]: return 0.1
        elif r <= quantiles.iloc[1]: return 0.3
        elif r <= quantiles.iloc[2]: return 0.5
        elif r <= quantiles.iloc[3]: return 0.7
        else: return 0.9
    cust["churn_prob_group"] = cust["recency_days"].apply(label_prob)
    cust["churn_label"] = (cust["recency_days"] > 90).astype(int)

    feature_cols = [
        "total_items", "total_spent", "total_orders", "unique_products",
        "avg_item_price", "price_std", "price_min", "price_max",
        "price_p25", "price_p75", "price_range", "price_cv",
        "purchase_span_days", "avg_purchase_interval", "recency_days",
        "avg_items_per_order", "avg_spend_per_order", "weekend_ratio",
        "avg_purchase_hour", "hour_std", "is_night", "is_weekday",
    ]

    features_df = cust[["CustomerID"] + feature_cols + ["churn_label", "churn_prob_group"]].copy()
    features_df = features_df.fillna(0)
    print(f"  特征维度: {len(feature_cols)} 维, {len(features_df)} 客户")

    # ─── 5. 标准化 ───
    print("\n[5/6] 特征标准化...")
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(features_df[feature_cols])
    print(f"  标准化矩阵: {X_scaled.shape}")

    # ─── 6. RFM 打分 ───
    print("\n[6/6] 计算RFM分数...")
    def r_score(r):
        if r <= 30: return 5
        elif r <= 90: return 4
        elif r <= 180: return 3
        elif r <= 365: return 2
        else: return 1

    def f_score(f):
        if f >= 20: return 5
        elif f >= 10: return 4
        elif f >= 5: return 3
        elif f >= 2: return 2
        else: return 1

    def m_score(m):
        if m >= 5000: return 5
        elif m >= 2000: return 4
        elif m >= 500: return 3
        elif m >= 100: return 2
        else: return 1

    recency = features_df["recency_days"].values
    frequency = features_df["total_orders"].values
    monetary = features_df["total_spent"].values

    rfm = pd.DataFrame({
        "CustomerID": features_df["CustomerID"].values,
        "recency": recency,
        "frequency": frequency,
        "monetary": monetary,
        "R_score": [r_score(x) for x in recency],
        "F_score": [f_score(x) for x in frequency],
        "M_score": [m_score(x) for x in monetary],
    })
    rfm["segment"] = rfm.apply(
        lambda row: "流失预警" if row["R_score"] <= 2
        else "高价值" if row["F_score"] >= 4 and row["M_score"] >= 4
        else "忠诚" if row["R_score"] >= 4 and row["F_score"] >= 3
        else "潜力" if row["R_score"] >= 3 and row["F_score"] >= 2
        else "一般", axis=1
    )

    # ─── 7. 月度聚合 & 购物篮 ───
    print("  生成月度数据和购物篮数据...")
    monthly = df.copy()
    monthly["YearMonth"] = monthly["InvoiceDate"].dt.strftime("%Y-%m")
    monthly_agg = monthly.groupby("YearMonth").agg(
        revenue=("LineTotal", "sum"),
        orders=("InvoiceNo", "nunique"),
        customers=("CustomerID", "nunique"),
    ).reset_index()
    monthly_agg["ds"] = pd.to_datetime(monthly_agg["YearMonth"] + "-01")
    monthly_agg["y"] = monthly_agg["revenue"]

    baskets = df.groupby("InvoiceNo")["StockCode"].agg(list).reset_index()
    baskets.columns = ["InvoiceNo", "StockCode"]

    # ─── 8. 保存 ───
    save_data = {
        "rfm": rfm,
        "features_df": features_df,
        "X_scaled": X_scaled,
        "feature_cols": feature_cols,
        "monthly": monthly_agg,
        "baskets": baskets,
    }

    with open(os.path.join(PREP_DIR, "phase2_preprocessed.pkl"), "wb") as f:
        pickle.dump(save_data, f)
    print(f"\n  Saved: phase2_preprocessed.pkl")
    print(f"  features_df: {features_df.shape}")
    print(f"  X_scaled: {X_scaled.shape}")
    print(f"  rfm: {rfm.shape}")
    print(f"  monthly: {monthly_agg.shape}")
    print(f"  baskets: {baskets.shape}")
    print(f"\n{'=' * 60}")
    print("  Phase 2 完成!")
    print(f"{'=' * 60}")

    return save_data


def run_preprocessing_standalone():
    return run_preprocessing()


if __name__ == "__main__":
    run_preprocessing_standalone()
