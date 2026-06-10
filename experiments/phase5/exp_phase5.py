"""
Phase 5 Optimization — 5 directions (weekly granularity)
A. log1p target transform
B. UK calendar features (holidays, payday, Christmas)
C. TimeSeriesSplit (validation) — already in baseline
D. ETS (Holt-Winters)
E. Ensemble: LightGBM + Prophet weighted
"""
import os, sys, warnings, pickle, json
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error
import lightgbm as lgb

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
EXP = os.path.join(ROOT, "experiments", "phase5")

def smape(actual, predicted):
    denominator = (np.abs(actual) + np.abs(predicted)) / 2.0
    mask = denominator > 0
    if mask.sum() == 0: return 0
    return np.mean(np.abs((actual[mask] - predicted[mask]) / denominator[mask])) * 100

def mape(actual, predicted):
    mask = actual > 0
    if mask.sum() == 0: return 0
    return np.mean(np.abs((actual[mask] - predicted[mask]) / actual[mask])) * 100

# Load and clean
df = pd.read_csv(os.path.join(RAW, "Online_Retail.csv"), encoding="latin1", parse_dates=["InvoiceDate"])
df["InvoiceNo"] = df["InvoiceNo"].astype(str)
df = df[~df["InvoiceNo"].str.startswith("C")]
df = df[df["Quantity"] > 0]; df = df[df["UnitPrice"] > 0]
for col in ["Quantity", "UnitPrice"]:
    q1, q3 = df[col].quantile([0.25, 0.75]); iqr = q3 - q1
    df = df[(df[col] >= q1 - 3*iqr) & (df[col] <= q3 + 3*iqr)]
df = df.dropna(subset=["CustomerID"])
df["CustomerID"] = df["CustomerID"].astype(int)
df["LineTotal"] = df["Quantity"] * df["UnitPrice"]

# Weekly aggregation (ISO week)
df["year_week"] = df["InvoiceDate"].dt.to_period("W-MON")
weekly = df.groupby("year_week").agg(revenue=("LineTotal", "sum"),
                                      orders=("InvoiceNo", "nunique"),
                                      customers=("CustomerID", "nunique"),
                                      quantity=("Quantity", "sum")).reset_index()
weekly["date"] = weekly["year_week"].dt.to_timestamp()
weekly = weekly.drop(columns=["year_week"]).sort_values("date").reset_index(drop=True)
print(f"Weekly: {len(weekly)} weeks, range {weekly['date'].min()} ~ {weekly['date'].max()}")
print(f"  Mean revenue: {weekly['revenue'].mean():,.0f}")

# UK holidays (2010-2012) and key retail dates
uk_holidays = pd.to_datetime([
    "2010-01-01", "2010-04-02", "2010-04-05", "2010-05-03", "2010-05-31",
    "2010-08-30", "2010-12-27", "2010-12-28",
    "2011-01-03", "2011-04-22", "2011-04-25", "2011-05-02", "2011-05-30",
    "2011-08-29", "2011-12-26", "2011-12-27",
    "2010-11-26",  # Black Friday 2010 (US, retail impact)
    "2011-11-25",  # Black Friday 2011
    "2010-12-25", "2011-12-25",  # Christmas
    "2010-11-11", "2011-11-11",  # Singles Day (China, growing UK influence)
])

def build_features_base(ts_df, target_col="revenue"):
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
    max_lag = max(lags)
    df_feat = df_feat.iloc[max_lag:].copy().reset_index(drop=True)
    return df_feat

def build_features_calendar(ts_df, target_col="revenue"):
    """Enhanced with UK calendar features."""
    df_feat = build_features_base(ts_df, target_col)
    # Days from/to nearest UK holiday
    df_feat["days_to_christmas"] = ((pd.to_datetime(df_feat["date"].dt.year.astype(str) + "-12-25") - df_feat["date"]).dt.days).clip(-30, 365)
    df_feat["is_christmas_season"] = ((df_feat["month"] >= 11) & (df_feat["month"] <= 12)).astype(int)
    df_feat["is_jan_sale"] = ((df_feat["month"] == 1)).astype(int)
    df_feat["is_black_friday_week"] = ((df_feat["month"] == 11) & (df_feat["week_of_year"] >= 47)).astype(int)
    # Holiday weeks: any week containing a UK holiday
    df_feat["has_holiday"] = 0
    for hd in uk_holidays:
        df_feat.loc[abs((df_feat["date"] - hd).dt.days) <= 7, "has_holiday"] = 1
    # Sin/cos seasonality encoding
    df_feat["month_sin"] = np.sin(2 * np.pi * df_feat["month"] / 12)
    df_feat["month_cos"] = np.cos(2 * np.pi * df_feat["month"] / 12)
    df_feat["woy_sin"] = np.sin(2 * np.pi * df_feat["week_of_year"] / 52)
    df_feat["woy_cos"] = np.cos(2 * np.pi * df_feat["week_of_year"] / 52)
    # End-of-month boost
    df_feat["is_month_end"] = (df_feat["date"].dt.day >= 25).astype(int)
    # Pre-Christmas peak weeks (49-52)
    df_feat["is_xmas_peak"] = ((df_feat["week_of_year"] >= 49) & (df_feat["week_of_year"] <= 52)).astype(int)
    return df_feat

feature_cols_base = [c for c in build_features_base(weekly).columns if c not in ["date", "revenue"]]
feature_cols_cal = [c for c in build_features_calendar(weekly).columns if c not in ["date", "revenue"]]
print(f"  Base features: {len(feature_cols_base)}, Calendar features: {len(feature_cols_cal)}")

# TimeSeriesSplit: use last 8 weeks as test
SPLIT = len(weekly) - 8
train_df = weekly.iloc[:SPLIT].copy()
test_df = weekly.iloc[SPLIT:].copy()
y_test = test_df["revenue"].values
print(f"  Train: {len(train_df)} weeks  Test: {len(test_df)} weeks")

# ═══ A. log1p target + LightGBM ═══
print("\n" + "="*70); print("A. log1p target + LightGBM (weekly, base features)"); print("="*70)
df_base = build_features_base(weekly)
X_all = df_base[feature_cols_base].values
y_all = df_base["revenue"].values
X_tr_a = X_all[:SPLIT-12]; y_tr_a = y_all[:SPLIT-12]
X_te_a = X_all[SPLIT-12:SPLIT-12+8]; y_te_a = y_all[SPLIT-12:SPLIT-12+8]
m_a = lgb.LGBMRegressor(n_estimators=500, learning_rate=0.05, num_leaves=31, max_depth=6,
                          min_child_samples=5, subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1, n_jobs=-1)
m_a.fit(X_tr_a, np.log1p(y_tr_a))
pred_a = np.expm1(m_a.predict(X_te_a))
pred_a = np.clip(pred_a, 0, None)
print(f"  SMAPE={smape(y_te_a, pred_a):.2f}%  MAPE={mape(y_te_a, pred_a):.2f}%  MAE={mean_absolute_error(y_te_a, pred_a):,.0f}  RMSE={np.sqrt(mean_squared_error(y_te_a, pred_a)):,.0f}")

# ═══ B. UK calendar features + LightGBM ═══
print("\n" + "="*70); print("B. UK Calendar features + LightGBM"); print("="*70)
df_cal = build_features_calendar(weekly)
X_all_cal = df_cal[feature_cols_cal].values
y_all_cal = df_cal["revenue"].values
X_tr_b = X_all_cal[:SPLIT-12]; y_tr_b = y_all_cal[:SPLIT-12]
X_te_b = X_all_cal[SPLIT-12:SPLIT-12+8]; y_te_b = y_all_cal[SPLIT-12:SPLIT-12+8]
m_b = lgb.LGBMRegressor(n_estimators=500, learning_rate=0.05, num_leaves=31, max_depth=6,
                          min_child_samples=5, subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1, n_jobs=-1)
m_b.fit(X_tr_b, y_tr_b)
pred_b = m_b.predict(X_te_b)
pred_b = np.clip(pred_b, 0, None)
print(f"  SMAPE={smape(y_te_b, pred_b):.2f}%  MAPE={mape(y_te_b, pred_b):.2f}%  MAE={mean_absolute_error(y_te_b, pred_b):,.0f}  RMSE={np.sqrt(mean_squared_error(y_te_b, pred_b)):,.0f}")

# ═══ C. TimeSeriesSplit CV on calendar features (for stable estimate) ═══
print("\n" + "="*70); print("C. TimeSeriesSplit CV (5-fold) — Calendar features + LightGBM"); print("="*70)
tscv = TimeSeriesSplit(n_splits=5)
cv_smape = []
for fold, (tr_idx, te_idx) in enumerate(tscv.split(X_all_cal)):
    Xtr, Xte = X_all_cal[tr_idx], X_all_cal[te_idx]
    ytr, yte = y_all_cal[tr_idx], y_all_cal[te_idx]
    m_c = lgb.LGBMRegressor(n_estimators=500, learning_rate=0.05, num_leaves=31, max_depth=6,
                              min_child_samples=5, subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1, n_jobs=-1)
    m_c.fit(Xtr, ytr)
    pred_c = np.clip(m_c.predict(Xte), 0, None)
    s = smape(yte, pred_c)
    cv_smape.append(s)
    print(f"  Fold {fold+1}: SMAPE={s:.2f}%")
print(f"  Mean SMAPE = {np.mean(cv_smape):.2f}% ± {np.std(cv_smape):.2f}%")

# ═══ D. ETS (Holt-Winters) ═══
print("\n" + "="*70); print("D. ETS / Holt-Winters (statsmodels)"); print("="*70)
try:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    ets_train = weekly["revenue"].iloc[:SPLIT].values
    ets_test = weekly["revenue"].iloc[SPLIT:].values
    ets_model = ExponentialSmoothing(ets_train, trend="add", seasonal="add", seasonal_periods=52).fit(optimized=True)
    pred_d = ets_model.forecast(steps=8)
    pred_d = np.clip(pred_d, 0, None)
    print(f"  SMAPE={smape(ets_test, pred_d):.2f}%  MAPE={mape(ets_test, pred_d):.2f}%  MAE={mean_absolute_error(ets_test, pred_d):,.0f}  RMSE={np.sqrt(mean_squared_error(ets_test, pred_d)):,.0f}")
except Exception as e:
    print(f"  Failed: {e}")
    pred_d = None

# ═══ E. Ensemble: LightGBM + Prophet weighted ═══
print("\n" + "="*70); print("E. Ensemble: LightGBM(calendar) + Prophet (weighted 0.6/0.4)"); print("="*70)
try:
    from prophet import Prophet
    # Prophet on weekly
    df_p = weekly[["date", "revenue"]].rename(columns={"date": "ds", "revenue": "y"})
    p_train = df_p.iloc[:SPLIT]
    p_test = df_p.iloc[SPLIT:][["ds"]]
    prophet = Prophet(yearly_seasonality=True, weekly_seasonality=False, daily_seasonality=False)
    prophet.fit(p_train)
    fc = prophet.predict(p_test)
    pred_prophet = np.clip(fc["yhat"].values, 0, None)
    # Align with calendar LightGBM prediction
    y_te_e = y_test  # same 8 weeks
    pred_e = 0.6 * pred_b + 0.4 * pred_prophet
    print(f"  Prophet only: SMAPE={smape(y_te_e, pred_prophet):.2f}%")
    print(f"  LightGBM(cal) only: SMAPE={smape(y_te_e, pred_b):.2f}%")
    print(f"  Ensemble 0.6/0.4: SMAPE={smape(y_te_e, pred_e):.2f}%  MAPE={mape(y_te_e, pred_e):.2f}%  MAE={mean_absolute_error(y_te_e, pred_e):,.0f}  RMSE={np.sqrt(mean_squared_error(y_te_e, pred_e)):,.0f}")
except Exception as e:
    print(f"  Failed: {e}")
    pred_e = None

# ═══ F. baseline v2 (re-create for fair comparison) ═══
print("\n" + "="*70); print("F. BASELINE re-run: LightGBM(base) with decay=0.97"); print("="*70)
X_tr_f = X_all[:SPLIT-12]; y_tr_f = y_all[:SPLIT-12]
X_te_f = X_all[SPLIT-12:SPLIT-12+8]; y_te_f = y_all[SPLIT-12:SPLIT-12+8]
n = len(X_tr_f)
sw = np.array([0.97 ** (n - 1 - i) for i in range(n)])
sw = sw / sw.sum() * n
m_f = lgb.LGBMRegressor(n_estimators=500, learning_rate=0.05, num_leaves=31, max_depth=6,
                          min_child_samples=5, subsample=0.8, colsample_bytree=0.8, random_state=42, verbose=-1, n_jobs=-1)
m_f.fit(X_tr_f, y_tr_f, sample_weight=sw)
pred_f = np.clip(m_f.predict(X_te_f), 0, None)
smape_f = smape(y_te_f, pred_f)
mape_f = mape(y_te_f, pred_f)
print(f"  SMAPE={smape_f:.2f}%  MAPE={mape_f:.2f}%  MAE={mean_absolute_error(y_te_f, pred_f):,.0f}  RMSE={np.sqrt(mean_squared_error(y_te_f, pred_f)):,.0f}")

# ═══ Summary ═══
print("\n" + "="*70)
print("PHASE 5 Summary (baseline: SMAPE 5.25%, OOT shift 39.8%)")
print("="*70)
results = {
    "A_log_LightGBM":  {"smape": smape(y_te_a, pred_a), "mape": mape(y_te_a, pred_a), "pred": pred_a.tolist()},
    "B_cal_LightGBM":  {"smape": smape(y_te_b, pred_b), "mape": mape(y_te_b, pred_b), "pred": pred_b.tolist()},
    "F_baseline_decay": {"smape": smape_f, "mape": mape_f, "pred": pred_f.tolist()},
}
print(f"{'Method':<25} {'SMAPE':>8} {'MAPE':>8} {'vs_base':>10}")
for name, r in results.items():
    delta = r["smape"] - smape_f
    print(f"  {name:<23} {r['smape']:>8.2f}% {r['mape']:>8.2f}%  {delta:>+.2f}pp")

with open(os.path.join(EXP, "phase5_compare.json"), "w") as f:
    json.dump({k: {kk: vv for kk, vv in v.items() if kk != "pred"} for k, v in results.items()}, f, indent=2)
print(f"\nSaved -> {EXP}/phase5_compare.json")
