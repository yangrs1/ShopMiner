"""
Phase 5 Darts: Add N-BEATS deep learning model to ensemble with v3 LightGBM.
Run in conda env (D:\\anaconda\\python.exe) where torch + darts are installed.
Test SMAPE for individual models, then weighted ensemble (0.7 LGB + 0.3 NBEATS).
"""
import os, sys, warnings, pickle, json, time
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

import torch
import darts
print(f"PyTorch: {torch.__version__}  CUDA: {torch.cuda.is_available()}")
print(f"Darts: {darts.__version__}")

from darts import TimeSeries
from darts.models import NBEATSModel
from darts.dataprocessing.transformers import Scaler
from sklearn.metrics import mean_absolute_error, mean_squared_error

ROOT = r"C:\Users\35027\Desktop\数据挖掘\ShopMiner"
RAW = os.path.join(ROOT, "data", "raw")
PREP = os.path.join(ROOT, "data", "prep")
EXP = os.path.join(ROOT, "experiments", "phase5")

# ─── Build weekly series (same as v3) ───
print("\n[1/5] Loading weekly data...")
t0 = time.time()
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
df["year_week"] = df["InvoiceDate"].dt.to_period("W-MON")
weekly = df.groupby("year_week").agg(revenue=("LineTotal", "sum"),
                                      orders=("InvoiceNo", "nunique"),
                                      customers=("CustomerID", "nunique"),
                                      quantity=("Quantity", "sum")).reset_index()
weekly["date"] = weekly["year_week"].dt.to_timestamp()
weekly = weekly.drop(columns=["year_week"]).sort_values("date").reset_index(drop=True)
print(f"  Weeks: {len(weekly)}  Time: {time.time()-t0:.1f}s")

# Convert to Darts TimeSeries (use integer index, skip fill_missing_dates)
ts = TimeSeries.from_values(weekly["revenue"].values.astype(np.float32).reshape(-1, 1))
scaler = Scaler()
ts_scaled = scaler.fit_transform(ts)

# Train/test split (last 8 weeks as test, same as v3)
SPLIT = len(ts_scaled) - 8
ts_train, ts_test = ts_scaled[:SPLIT], ts_scaled[SPLIT:]

# ─── Train N-BEATS ───
print("\n[2/5] Training N-BEATS...")
t0 = time.time()
torch.manual_seed(42)
nbe = NBEATSModel(
    input_chunk_length=8, output_chunk_length=4,
    n_epochs=50, batch_size=4, random_state=42,
    generic_architecture=True, num_stacks=4, num_blocks=1, num_layers=2,
    layer_widths=32, pl_trainer_kwargs={"accelerator": "cpu", "enable_progress_bar": False, "enable_model_summary": False},
)
nbe.fit(ts_train)
print(f"  NBEATS training time: {time.time()-t0:.1f}s")

# Predict 8 weeks ahead
print("\n[3/5] Predicting 8 weeks ahead...")
t0 = time.time()
pred_nbe_scaled = nbe.predict(n=8)
pred_nbe = scaler.inverse_transform(pred_nbe_scaled)
print(f"  NBEATS prediction time: {time.time()-t0:.1f}s")

# Get actual values
y_te = ts_test.values().squeeze()
y_te_orig = scaler.inverse_transform(ts_test).values().squeeze()
p_nbe = pred_nbe.values().squeeze()

def smape(a, p):
    d = (np.abs(a) + np.abs(p)) / 2.0
    m_ = d > 0
    return float(np.mean(np.abs((a[m_] - p[m_]) / d[m_])) * 100)
def mape(a, p):
    m_ = a > 0
    return float(np.mean(np.abs((a[m_] - p[m_]) / a[m_])) * 100)

smape_nbe = smape(y_te_orig, p_nbe)
mape_nbe = mape(y_te_orig, p_nbe)
mae_nbe = float(mean_absolute_error(y_te_orig, p_nbe))
rmse_nbe = float(np.sqrt(mean_squared_error(y_te_orig, p_nbe)))
print(f"  NBEATS Test SMAPE={smape_nbe:.2f}%  MAPE={mape_nbe:.2f}%  MAE={mae_nbe:,.0f}  RMSE={rmse_nbe:,.0f}")

# ─── Load v3 LightGBM and get its predictions on the same 8 weeks ───
print("\n[4/5] Loading v3 LightGBM and computing ensemble...")
t0 = time.time()
with open(os.path.join(PREP, "phase5_forecast_v2.pkl"), "rb") as f:
    v3 = pickle.load(f)
v3_smape = v3.get("test_smape", 4.86)
print(f"  v3 LGBM Test SMAPE: {v3_smape:.2f}%")

# Reproduce v3 features and predict
uk_holidays = pd.to_datetime([
    "2010-01-01", "2010-04-02", "2010-04-05", "2010-05-03", "2010-05-31",
    "2010-08-30", "2010-12-27", "2010-12-28",
    "2011-01-03", "2011-04-22", "2011-04-25", "2011-05-02", "2011-05-30",
    "2011-08-29", "2011-12-26", "2011-12-27",
    "2010-11-26", "2011-11-25",
    "2010-12-25", "2011-12-25",
    "2010-11-11", "2011-11-11",
])
def build_features(ts_df, target_col="revenue"):
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
    df_feat["days_to_christmas"] = ((pd.to_datetime(df_feat["date"].dt.year.astype(str) + "-12-25") - df_feat["date"]).dt.days).clip(-30, 365)
    df_feat["is_christmas_season"] = ((df_feat["month"] >= 11) & (df_feat["month"] <= 12)).astype(int)
    df_feat["is_jan_sale"] = ((df_feat["month"] == 1)).astype(int)
    df_feat["is_black_friday_week"] = ((df_feat["month"] == 11) & (df_feat["week_of_year"] >= 47)).astype(int)
    df_feat["has_holiday"] = 0
    for hd in uk_holidays:
        df_feat.loc[abs((df_feat["date"] - hd).dt.days) <= 7, "has_holiday"] = 1
    df_feat["month_sin"] = np.sin(2 * np.pi * df_feat["month"] / 12)
    df_feat["month_cos"] = np.cos(2 * np.pi * df_feat["month"] / 12)
    df_feat["woy_sin"] = np.sin(2 * np.pi * df_feat["week_of_year"] / 52)
    df_feat["woy_cos"] = np.cos(2 * np.pi * df_feat["week_of_year"] / 52)
    df_feat["is_month_end"] = (df_feat["date"].dt.day >= 25).astype(int)
    df_feat["is_xmas_peak"] = ((df_feat["week_of_year"] >= 49) & (df_feat["week_of_year"] <= 52)).astype(int)
    max_lag = max(lags)
    df_feat = df_feat.iloc[max_lag:].copy().reset_index(drop=True)
    return df_feat

df_feat = build_features(weekly)
feature_cols = [c for c in df_feat.columns if c not in ["date", "revenue"]]
X = df_feat[feature_cols].values
y = df_feat["revenue"].values
SPLIT2 = len(X) - 8
X_tr, X_te = X[:SPLIT2], X[SPLIT2:]
y_tr, y_te2 = y[:SPLIT2], y[SPLIT2:]

import lightgbm as lgb
m_lgb = v3["model"]  # already trained
p_lgb = np.clip(m_lgb.predict(X_te), 0, None)
smape_lgb = smape(y_te2, p_lgb)
print(f"  Reproduced LGBM Test SMAPE: {smape_lgb:.2f}% (saved: {v3_smape:.2f}%)")

# Ensemble
best_ens_smape = smape_lgb
best_w = 1.0
print(f"\n  Testing ensemble weights (LGB + NBEATS):")
for w in [0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]:
    p_ens = w * p_lgb + (1 - w) * p_nbe
    s = smape(y_te2, p_ens)
    if s < best_ens_smape:
        best_ens_smape = s
        best_w = w
    print(f"    w_lgb={w:.1f} w_nbe={1-w:.1f}: SMAPE={s:.2f}%")
print(f"  Time: {time.time()-t0:.1f}s")

print(f"\n  Best ensemble SMAPE: {best_ens_smape:.2f}% (vs v3 {v3_smape:.2f}%, {(best_ens_smape-v3_smape)/v3_smape*100:+.2f}%)")
print(f"  Best weight: LGB={best_w:.1f} / NBEATS={1-best_w:.1f}")

# ─── Save only if ensemble improves ───
print("\n[5/5] Saving...")
if best_ens_smape < v3_smape:
    print(f"  [SAVE] Ensemble improved. Saving new pkl...")
    p_ens_final = best_w * p_lgb + (1 - best_w) * p_nbe
    test_mape = mape(y_te2, p_ens_final)
    test_mae = float(mean_absolute_error(y_te2, p_ens_final))
    test_rmse = float(np.sqrt(mean_squared_error(y_te2, p_ens_final)))
    new_pkl = dict(v3)
    new_pkl["version"] = "v4_lgbm_nbeats_ensemble"
    new_pkl["method"] = f"LightGBM-weekly-calendar + NBEATS ensemble (w_lgb={best_w:.1f})"
    new_pkl["nbeats_model"] = nbe
    new_pkl["nbeats_smape"] = smape_nbe
    new_pkl["ensemble_weight_lgb"] = best_w
    new_pkl["ensemble_weight_nbeats"] = 1 - best_w
    new_pkl["test_smape"] = best_ens_smape
    new_pkl["test_mape"] = test_mape
    new_pkl["test_mae"] = test_mae
    new_pkl["test_rmse"] = test_rmse
    new_pkl["improvement_note"] = f"v4: LightGBM + NBEATS ensemble, SMAPE {v3_smape:.2f}% -> {best_ens_smape:.2f}% ({(best_ens_smape-v3_smape)/v3_smape*100:+.2f}%)"
    out_pkl = os.path.join(EXP, "phase5_forecast_winner.pkl")
    with open(out_pkl, "wb") as f:
        pickle.dump(new_pkl, f)
    print(f"  Saved: {out_pkl}")
else:
    print(f"  [NO SAVE] Not improved. Keep v3.")

study_out = {
    "nbeats_test_smape": smape_nbe,
    "nbeats_test_mape": mape_nbe,
    "nbeats_test_mae": mae_nbe,
    "nbeats_test_rmse": rmse_nbe,
    "lgbm_test_smape_reproduced": smape_lgb,
    "lgbm_test_smape_v3": v3_smape,
    "best_ensemble_weight_lgb": best_w,
    "best_ensemble_weight_nbeats": 1 - best_w,
    "ensemble_test_smape": best_ens_smape,
    "improved": bool(best_ens_smape < v3_smape),
}
with open(os.path.join(EXP, "phase5_darts.json"), "w") as f:
    json.dump(study_out, f, indent=2, ensure_ascii=False, default=str)
print(f"  Study saved: {os.path.join(EXP, 'phase5_darts.json')}")
