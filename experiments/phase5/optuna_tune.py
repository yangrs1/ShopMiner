"""
Phase 5 Optuna: Tune LightGBM for weekly sales forecast.
Objective: SMAPE on temporal validation (last 8 weeks held out)
Final check: re-fit on all data + test on last 8 weeks
"""
import os, sys, warnings, pickle, json, time
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

import optuna
from optuna.samplers import TPESampler
optuna.logging.set_verbosity(optuna.logging.WARNING)

import lightgbm as lgb
from sklearn.metrics import mean_absolute_error, mean_squared_error

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
PREP = os.path.join(ROOT, "data", "prep")
EXP = os.path.join(ROOT, "experiments", "phase5")

# ─── Build features (replicate v3 build_winner.py) ───
print("[1/5] Building weekly features...")
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

uk_holidays = pd.to_datetime([
    "2010-01-01", "2010-04-02", "2010-04-05", "2010-05-03", "2010-05-31",
    "2010-08-30", "2010-12-27", "2010-12-28",
    "2011-01-03", "2011-04-22", "2011-04-25", "2011-05-02", "2011-05-30",
    "2011-08-29", "2011-12-26", "2011-12-27",
    "2010-11-26", "2011-11-25",
    "2010-12-25", "2011-12-25",
    "2010-11-11", "2011-11-11",
])

def build_features_calendar(ts_df, target_col="revenue"):
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

df_feat = build_features_calendar(weekly)
feature_cols = [c for c in df_feat.columns if c not in ["date", "revenue"]]
X = df_feat[feature_cols].values
y = df_feat["revenue"].values
print(f"  Features: {len(feature_cols)}  Rows: {len(X)}")

# Train/val split: last 8 weeks as test (same as v3)
SPLIT = len(X) - 8
X_tr, X_te = X[:SPLIT], X[SPLIT:]
y_tr, y_te = y[:SPLIT], y[SPLIT:]

# Within train, hold out last 4 weeks as VAL for Optuna
VAL_SPLIT = len(X_tr) - 4
X_t, X_v = X_tr[:VAL_SPLIT], X_tr[VAL_SPLIT:]
y_t, y_v = y_tr[:VAL_SPLIT], y_tr[VAL_SPLIT:]

def smape(a, p):
    d = (np.abs(a) + np.abs(p)) / 2.0
    m_ = d > 0
    return float(np.mean(np.abs((a[m_] - p[m_]) / d[m_])) * 100)

# ─── Optuna objective: minimize SMAPE on VAL ───
print("\n[2/5] Optuna search (60 trials, minimize VAL SMAPE)...")
t0 = time.time()
def objective(trial):
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 200, 1500, step=100),
        "learning_rate": trial.suggest_float("learning_rate", 0.005, 0.2, log=True),
        "num_leaves": trial.suggest_int("num_leaves", 7, 127),
        "max_depth": trial.suggest_int("max_depth", 3, 12),
        "min_child_samples": trial.suggest_int("min_child_samples", 2, 30),
        "subsample": trial.suggest_float("subsample", 0.5, 1.0),
        "subsample_freq": 1,
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
    }
    m = lgb.LGBMRegressor(**params, random_state=42, verbose=-1, n_jobs=-1)
    m.fit(X_t, y_t)
    p = np.clip(m.predict(X_v), 0, None)
    return smape(y_v, p)

study = optuna.create_study(direction="minimize", sampler=TPESampler(seed=42))
study.optimize(objective, n_trials=60, show_progress_bar=False)
print(f"  Best VAL SMAPE: {study.best_value:.2f}%")
print(f"  Best params: {study.best_params}")
print(f"  Time: {time.time()-t0:.1f}s")

# ─── Train final model on full train (cutoff before test) with best params ───
print("\n[3/5] Training final model on full train...")
t0 = time.time()
best_params = study.best_params.copy()
best_params.update({"random_state": 42, "verbose": -1, "n_jobs": -1, "subsample_freq": 1})
m_final = lgb.LGBMRegressor(**best_params)
m_final.fit(X_tr, y_tr)
pred = np.clip(m_final.predict(X_te), 0, None)
test_smape = smape(y_te, pred)
test_mape = float(np.mean(np.abs((y_te[y_te > 0] - pred[y_te > 0]) / y_te[y_te > 0])) * 100)
test_mae = float(mean_absolute_error(y_te, pred))
test_rmse = float(np.sqrt(mean_squared_error(y_te, pred)))
print(f"  Test SMAPE={test_smape:.2f}%  MAPE={test_mape:.2f}%  MAE={test_mae:,.0f}  RMSE={test_rmse:,.0f}")
print(f"  Time: {time.time()-t0:.1f}s")

# ─── Compare vs current winner ───
print("\n[4/5] Loading current v3 winner...")
with open(os.path.join(PREP, "phase5_forecast_v2.pkl"), "rb") as f:
    v3 = pickle.load(f)
v3_smape = v3.get("test_smape", 4.86)
print(f"  Current Test SMAPE: {v3_smape:.2f}%")
print(f"  New Test SMAPE: {test_smape:.2f}% ({(test_smape-v3_smape)/v3_smape*100:+.2f}%)")

# ─── Save new pkl only if improved ───
if test_smape < v3_smape:
    print("\n[5/5] SMAPE improved, building new winner pkl...")
    new_pkl = dict(v3)
    new_pkl["version"] = "v4_lgbm_optuna"
    new_pkl["model"] = m_final
    new_pkl["method"] = "LightGBM-weekly-calendar-Optuna"
    new_pkl["optuna_best_params"] = study.best_params
    new_pkl["optuna_best_val_smape"] = study.best_value
    new_pkl["optuna_n_trials"] = 60
    new_pkl["test_smape"] = test_smape
    new_pkl["test_mape"] = test_mape
    new_pkl["test_mae"] = test_mae
    new_pkl["test_rmse"] = test_rmse
    new_pkl["improvement_note"] = f"v4: Optuna-tuned LightGBM, SMAPE {v3_smape:.2f}% -> {test_smape:.2f}% ({(test_smape-v3_smape)/v3_smape*100:+.2f}%)"

    out_pkl = os.path.join(EXP, "phase5_forecast_winner.pkl")
    with open(out_pkl, "wb") as f:
        pickle.dump(new_pkl, f)
    print(f"  Saved: {out_pkl}")
else:
    print(f"\n[NO SAVE] SMAPE not improved ({test_smape:.2f}% >= {v3_smape:.2f}%). Keep v3.")

study_out = {
    "best_value_val_smape": study.best_value,
    "best_params": study.best_params,
    "n_trials": 60,
    "test_smape": test_smape,
    "test_mape": test_mape,
    "test_mae": test_mae,
    "test_rmse": test_rmse,
    "smape_improved": test_smape < v3_smape,
    "baseline_smape": v3_smape,
}
with open(os.path.join(EXP, "phase5_optuna.json"), "w") as f:
    json.dump(study_out, f, indent=2, ensure_ascii=False)
print(f"\nStudy saved: {os.path.join(EXP, 'phase5_optuna.json')}")
