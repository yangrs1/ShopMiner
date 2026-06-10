"""
Phase 5 Optuna v2: Use TimeSeriesSplit CV (5-fold) instead of single VAL.
Objective: mean SMAPE across 5 temporal folds (more robust than single holdout).
"""
import os, sys, warnings, pickle, json, time
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")

import optuna
from optuna.samplers import TPESampler
optuna.logging.set_verbosity(optuna.logging.WARNING)

import lightgbm as lgb
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_absolute_error, mean_squared_error

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RAW = os.path.join(ROOT, "data", "raw")
PREP = os.path.join(ROOT, "data", "prep")
EXP = os.path.join(ROOT, "experiments", "phase5")

# ─── Build features (same as v1) ───
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
print(f"  Weeks: {len(weekly)}  Features: {len(feature_cols)}  Rows: {len(X)}  Time: {time.time()-t0:.1f}s")

# Final test: last 8 weeks (same as v3)
SPLIT = len(X) - 8
X_tr_full, X_te = X[:SPLIT], X[SPLIT:]
y_tr_full, y_te = y[:SPLIT], y[SPLIT:]

def smape(a, p):
    d = (np.abs(a) + np.abs(p)) / 2.0
    m_ = d > 0
    return float(np.mean(np.abs((a[m_] - p[m_]) / d[m_])) * 100)

# ─── Optuna objective: mean SMAPE across 5 TimeSeriesSplit folds ───
print("\n[2/5] Optuna search (40 trials, TimeSeriesSplit CV-5)...")
t0 = time.time()
def objective(trial):
    params = {
        "n_estimators": trial.suggest_int("n_estimators", 200, 1000, step=100),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.15, log=True),
        "num_leaves": trial.suggest_int("num_leaves", 7, 63),
        "max_depth": trial.suggest_int("max_depth", 3, 10),
        "min_child_samples": trial.suggest_int("min_child_samples", 2, 20),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "subsample_freq": 1,
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-6, 5.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 1e-6, 5.0, log=True),
    }
    tscv = TimeSeriesSplit(n_splits=5)
    fold_smapes = []
    for tr_idx, va_idx in tscv.split(X_tr_full):
        m = lgb.LGBMRegressor(**params, random_state=42, verbose=-1, n_jobs=-1)
        m.fit(X_tr_full[tr_idx], y_tr_full[tr_idx])
        p = np.clip(m.predict(X_tr_full[va_idx]), 0, None)
        fold_smapes.append(smape(y_tr_full[va_idx], p))
    return float(np.mean(fold_smapes))

study = optuna.create_study(direction="minimize", sampler=TPESampler(seed=42))
study.optimize(objective, n_trials=40, show_progress_bar=False)
print(f"  Best CV SMAPE: {study.best_value:.2f}%")
print(f"  Best params: {study.best_params}")
print(f"  Time: {time.time()-t0:.1f}s")

# ─── Train final model on full train (no holdout) with best params ───
print("\n[3/5] Training final model on full train...")
t0 = time.time()
best_params = study.best_params.copy()
best_params.update({"random_state": 42, "verbose": -1, "n_jobs": -1, "subsample_freq": 1})
m_final = lgb.LGBMRegressor(**best_params)
m_final.fit(X_tr_full, y_tr_full)
pred = np.clip(m_final.predict(X_te), 0, None)
test_smape = smape(y_te, pred)
test_mape = float(np.mean(np.abs((y_te[y_te > 0] - pred[y_te > 0]) / y_te[y_te > 0])) * 100)
test_mae = float(mean_absolute_error(y_te, pred))
test_rmse = float(np.sqrt(mean_squared_error(y_te, pred)))
print(f"  Test SMAPE={test_smape:.2f}%  MAPE={test_mape:.2f}%  MAE={test_mae:,.0f}  RMSE={test_rmse:,.0f}")
print(f"  Time: {time.time()-t0:.1f}s")

# ─── Compare ───
print("\n[4/5] Loading current v3 winner...")
with open(os.path.join(PREP, "phase5_forecast_v2.pkl"), "rb") as f:
    v3 = pickle.load(f)
v3_smape = v3.get("test_smape", 4.86)
print(f"  Current Test SMAPE: {v3_smape:.2f}%")
print(f"  New Test SMAPE: {test_smape:.2f}% ({(test_smape-v3_smape)/v3_smape*100:+.2f}%)")

# ─── Save only if improved ───
if test_smape < v3_smape:
    print("\n[5/5] SMAPE improved, building new winner pkl...")
    new_pkl = dict(v3)
    new_pkl["version"] = "v4_lgbm_optuna_cv"
    new_pkl["model"] = m_final
    new_pkl["method"] = "LightGBM-weekly-calendar-OptunaCV"
    new_pkl["optuna_best_params"] = study.best_params
    new_pkl["optuna_best_cv_smape"] = study.best_value
    new_pkl["optuna_n_trials"] = 40
    new_pkl["test_smape"] = test_smape
    new_pkl["test_mape"] = test_mape
    new_pkl["test_mae"] = test_mae
    new_pkl["test_rmse"] = test_rmse
    new_pkl["improvement_note"] = f"v4: Optuna-tuned LightGBM via TimeSeriesSplit CV-5, SMAPE {v3_smape:.2f}% -> {test_smape:.2f}% ({(test_smape-v3_smape)/v3_smape*100:+.2f}%)"

    out_pkl = os.path.join(EXP, "phase5_forecast_winner.pkl")
    with open(out_pkl, "wb") as f:
        pickle.dump(new_pkl, f)
    print(f"  Saved: {out_pkl}")
else:
    print(f"\n[NO SAVE] SMAPE not improved ({test_smape:.2f}% >= {v3_smape:.2f}%). Keep v3.")

study_out = {
    "best_value_cv_smape": study.best_value,
    "best_params": study.best_params,
    "n_trials": 40,
    "test_smape": test_smape,
    "test_mape": test_mape,
    "test_mae": test_mae,
    "test_rmse": test_rmse,
    "smape_improved": bool(test_smape < v3_smape),
    "baseline_smape": v3_smape,
}
with open(os.path.join(EXP, "phase5_optuna.json"), "w") as f:
    json.dump(study_out, f, indent=2, ensure_ascii=False, default=str)
print(f"\nStudy saved: {os.path.join(EXP, 'phase5_optuna.json')}")
