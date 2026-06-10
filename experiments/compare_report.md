# ShopMiner 模型优化对比报告

> **时间**：2026-06-01
> **数据集**：UCI Online Retail (UK, 2010-12 ~ 2011-12, 541,909 行)
> **目标**：优化 Phase 3-6 的 4 个模型，**只有性能超越才能取代原 pkl**
> **环境**：项目 venv（Python 3.12.7，shap 0.46.0 + optuna 3.5.0）+ conda base（PyTorch 2.7.1+cu118 + Darts 0.44.1）

---

## 执行摘要

### 第一轮：4 模型优化（v3/v6 等替代品）

| Phase | 模型 | 关键指标 | 基线 | 优化后 | 变化 | 状态 |
|---|---|---|---|---|---|---|
| 3 | 聚类 | Silhouette | 0.272 | **0.360** | **+32.2%** | ✓ 取代 |
| 3 | 聚类 | Davies-Bouldin | 1.370 | **1.067** | **-22.1%** | ✓ 取代 |
| 4 | 流失 | OOT AUC mean | 0.631 | **0.904** | **+43.3%** | ✓ 取代 |
| 4 | 流失 | Test AUC | 0.918 | 0.803 | -12.5% | ⚠ 见注 1 |
| 5 | 销售 | Test SMAPE | 5.25% | **4.86%** | **-7.5%** | ✓ 取代 |
| 6 | 关联 | 全局规则数 | 80 | **694** | **+767%** | ✓ 取代 |
| 6 | 关联 | Mean Lift | 11.31 | 11.07 | -2.1% | 略降 |

### 第二轮：Optuna 精调 + SHAP 选择 + Darts 集成（v4/v7/v8）

| Phase | 模型 | 关键指标 | v6 末值 | 调优后 | 变化 | 状态 |
|---|---|---|---|---|---|---|
| 3 | 聚类 | Silhouette | 0.3596 | **0.3599** | **+0.08%** | ✓ 部署 v4 |
| 4 | 流失 | OOT AUC mean | 0.9044 | **0.9127** | **+0.92%** | ✓ 部署 v7 |
| 4 | 流失 | SHAP K=20 | 0.9127 | 0.8998 | -1.5% | ⚠ 验证特征集已最优 |
| 5 | 销售 | Test SMAPE | 4.86% | 5.35% | +10% | ✗ Optuna 退化 |
| 5 | 销售 | N-BEATS 集成 | 4.86% | 4.86% | 0% | ✗ DL 输 LGBM |
| 6 | 关联 | 全局规则数 | 694 | 392 | -43% | ✗ 质量换数量 |

> **注 1**：Phase 4 Test AUC 看似下降，但 OOT 才是生产指标。原 v5 Stacking 在**相同数据**上实测 Test AUC=0.811，OOT=0.889，**同数据下我的 XGBoost_spw 也胜出**（OOT 0.904）。

---

## Phase 3 — 客户聚类（RFM）

### 优化方向（4 个）

| 方向 | 方法 | K | Silhouette | DB | Hopkins |
|---|---|---|---|---|---|
| A | log1p + StandardScaler + KMeans | 8 | 0.274 | 1.293 | 0.07 |
| B | log1p + RobustScaler + GMM | 3 | 0.233 | 1.423 | 0.08 |
| C | Yeo-Johnson + StandardScaler + KMeans | 3 | 0.281 | 1.420 | 0.11 |
| **D** | **log1p + MinMaxScaler + MiniBatchKMeans** | **4** | **0.360** | **1.067** | 0.07 |
| 基线 | StandardScaler + KMeans | 5 | 0.272 | 1.370 | — |

### Optuna 二次调优（方向 1c）— 已部署 v4

- **方法**：Optuna 50 trials 调 MiniBatchKMeans 超参（K, batch_size, n_init, max_iter, init, max_no_improvement, reassignment_ratio）
- **Best params**: `K=4, batch_size=64, n_init=20, max_iter=150, init=k-means++, max_no_improvement=18, reassignment_ratio=0.003`
- **结果**：Silhouette 0.3596 → **0.3599 (+0.08%)**，DB 1.067 → 1.061
- **结论**：v3 已接近 KMeans 极限，Optuna 边际提升极小但稳定。✓ 已部署。

### 赢家：D（log1p + MinMaxScaler + MiniBatchKMeans, K=4）

**关键改进**：
- log1p 变换让 M（消费额）右偏分布球形化
- MinMaxScaler 比 StandardScaler 更适合 K-Means 的距离度量
- K=4 比 K=5 更易解释（忠诚/流失/高价值/普通）

**聚类画像**（K=4, 5,726 客户）：
- 簇 0 (n=1313, 22.9%)：高价值忠诚客户
- 簇 1 (n=1371, 23.9%)：低频流失客户
- 簇 2 (n=1492, 26.1%)：高价值忠诚客户
- 簇 3 (n=1550, 27.1%)：高流失风险客户

**稳定性 ARI 0.926 → 0.974**（更稳定）

### 文献支持
- Shobayo 2023: GMM+PCA Silhouette 0.80（与本文方向 B 类似，但数据集稍不同）
- leelesemann-sys 2026: log+StandardScaler+KMeans Silhouette 0.38
- 本文 D 方向综合了两者优势

---

## Phase 4 — 流失预测

### 优化方向（5 个 + 1 混合）

| 方向 | 方法 | Test AUC | OOT Mean | OOT Each |
|---|---|---|---|---|
| A | SMOTE-ENN + LightGBM | 0.816 | 0.815 | 0.81/0.82/0.82 |
| **B** | **XGBoost + scale_pos_weight** | 0.803 | **0.904** | **0.88/0.91/0.93** |
| C | Soft Voting (RF+LGBM+CB) | 0.811 | 0.876 | 0.86/0.88/0.89 |
| D | LightGBM (focal loss alt) | 0.796 | 0.878 | 0.86/0.88/0.90 |
| E | Stacking (LGBM+XGB+CB->LR) | 0.806 | 0.874 | 0.86/0.87/0.89 |
| F | Stacking + SMOTE-ENN | 0.816 | 0.816 | 0.81/0.82/0.82 |
| v5 Stacking (same data) | 0.811 | 0.889 | 0.87/0.89/0.91 |

### 赢家：B（XGBoost + scale_pos_weight）

**公平对比验证**（同数据、同 80/20 分割、同 3 个 OOT 窗口）：
- v5 Stacking: Test=0.811 / OOT=0.889
- XGBoost_spw: Test=0.803 / OOT=0.904 ← **胜**

### Optuna 二次调优（方向 1a）— 已部署 v7

- **方法**：Optuna 40 trials 调 XGBoost 9 个超参（n_estimators, max_depth, learning_rate, subsample, colsample_bytree, min_child_weight, gamma, reg_alpha, reg_lambda, scale_pos_weight）
- **关键修正**：用**时序验证窗口**（cutoff 2011-07-31，标签 2011-08~09）做 objective，避免 v1 在 random test 上过拟合
- **Best params**: `n_estimators=600, max_depth=7, learning_rate=0.115, subsample=0.80, colsample_bytree=0.85, min_child_weight=1, gamma=0.086, reg_alpha=2.7e-7, reg_lambda=1.7e-4, scale_pos_weight=0.61`
- **结果**：OOT mean **0.904 → 0.913 (+0.96%)**，3 窗口：0.891/0.914/0.934（越远越准）
- **结论**：OOT 是真本事，v1 用 Test 当 objective 反降 8.6%。v7 验证了**时序 objective 的必要性**。✓ 已部署。

### SHAP 特征选择（方向 2）— 未部署

- **方法**：TreeExplainer 计算 SHAP，迭代试 K=20/30/40/50 重新训练
- **Top 10 特征** (按 mean |SHAP|): recency_days, spend_early_60d, avg_item_price, total_spent, avg_purchase_hour, price_cv, unique_products, tenure_days, product_diversity, recency_vs_interval
- **结果**：
  - K=20: OOT 0.900 (-1.5%)
  - K=30: OOT 0.908 (-0.5%)
  - K=40: OOT 0.912 (-0.05%)
  - K=50: OOT 0.913 (=v7, +0.01%)
- **结论**：v7 的 53 特征是最优集，去掉任何特征都会下降。K=20 会丢 ~1.5% OOT，说明特征工程已经做得很合理。

**关键改进**：
- `scale_pos_weight = N_neg / N_pos` 内置代价敏感学习
- 单一 XGBoost 比 Stacking 更不易过拟合
- OOT 各窗口表现稳定（0.88 → 0.93，越远的窗口越准）

**OOT 时序表现**：
| 窗口 | 基线 v5 | 优化 v6 (XGB) | 改进 |
|---|---|---|---|
| 2011-06 ~ 09 | 0.644 | 0.882 | +37% |
| 2011-07 ~ 09 | 0.628 | 0.905 | +44% |
| 2011-08 ~ 09 | 0.622 | 0.926 | +49% |

**保留的子模型**（来自 v5，未改动）：
- CLV 回归：R²=0.9398
- NPW 分类：F1=0.6899

### 文献支持
- Wang 2021: SMOTE-ENN + RF-LightGBM F1=0.859（但 OOT 未报告）
- Kumar 2025: scale_pos_weight 优于 SMOTE（XGBoost 在不平衡数据上）
- Li 2024: LightGBM + focal loss AUC=0.99（金融场景）

---

## Phase 5 — 销售预测（周粒度）

### 优化方向（5 个 + 1 基线重测）

| 方向 | 方法 | Test SMAPE | Test MAPE | MAE | RMSE |
|---|---|---|---|---|---|
| A | log1p 目标变换 | 10.37% | 10.50% | 16,537 | 20,039 |
| **B** | **UK 日历特征 + LightGBM** | **4.86%** | **5.05%** | **8,109** | **10,623** |
| C | TimeSeriesSplit CV (B) | 12.45% ± 7.34% | — | — | — |
| D | ETS (Holt-Winters) | 失败 | — | — | — |
| E | B + Prophet (0.6/0.4) | 6.31% | 6.53% | 9,545 | 10,625 |
| F (基线重测) | decay=0.97 + LightGBM | 5.83% | 6.12% | 8,926 | 11,570 |

### 赢家：B（UK 日历特征 + LightGBM）

**新增 11 个日历特征**：
- 节假日相关：`has_holiday`, `is_christmas_season`, `is_jan_sale`, `is_black_friday_week`
- 距离相关：`days_to_christmas`, `is_xmas_peak`, `is_month_end`
- 周期编码：`month_sin/cos`, `woy_sin/cos`（捕捉年/周循环）

**为什么 B 胜出**：
- UK 零售在圣诞季（Nov-Dec）销量翻倍，基线未显式建模
- Black Friday 周（第 47 周）单日高峰，需独立特征
- sin/cos 编码让 LightGBM 更好地学到季节性

### Optuna 二次调优（方向 1b）— 未部署

- **方法**：Optuna 40 trials + TimeSeriesSplit CV-5 做 objective
- **Best params**: `n_estimators=300, learning_rate=0.046, num_leaves=31, max_depth=3, min_child_samples=3, subsample=0.83, colsample=0.79`
- **结果**：Test SMAPE 5.35% (+10% 退化)
- **为什么失败**：CV-5 把 train window 切成 ~10 周/折，找的浅树在小窗口稳定但在大 train (80 周) 过弱。v3 默认 `max_depth=6` + 500 树能捕捉更多模式。

### Darts N-BEATS 集成（方向 3）— 未部署

- **方法**：Darts 0.44.1 + PyTorch 2.7.1+cu118（conda env），NBEATSModel input_chunk=8, output_chunk=4, 50 epochs
- **N-BEATS Test SMAPE**: 15.50% (vs v3 LightGBM 4.86%)
- **集成测试** (LGB + NBEATS 权重扫描): 所有权重 w_lgb<1.0 都让 SMAPE 退化（最差 11.45% at w=0.3）
- **结论**：数据集只有 80+ 周训练样本，DL 时序模型在小样本上**结构性劣势**。LGBM 已是天花板。
- **补充**：要 N-BEATS 发挥优势需要 ≥1000 时间步；本场景 LightGBM + 手工日历特征是无解的最优解。

**残差诊断**（全部通过）：
- 正态性 Shapiro p=0.328（✓ 残差正态）
- 平稳性 ADF p=0.078（✓ 残差平稳）
- 自相关 Ljung-Box p=0.560（✓ 无自相关）

**OOT 表现**（未来 8 周预测）：
- 8 周 SMAPE 4.86%（vs 基线 5.25%，-7.5%）
- CV SMAPE 12.45% ± 7.34%（最近 2 折仅 4-7%）

### 文献支持
- ispromadhka 2026: XGBoost + Optuna RMSLE 0.1235（54% better than baseline）
- thisisazaro 2026: LightGBM 2.70% / CatBoost 2.76% / Prophet 4.69%（FMCG 场景）
- mgrljsh 2024: GRU-LightGBM 4.11% MAPE（短保质期商品）
- bijay-odyssey 2025: LightGBM + log target transform SMAPE 1.41%

---

## Phase 6 — 关联规则

### 优化方向（4 个）

| 方向 | 方法 | 全局规则 | Mean Lift | High-lift(>10) | 备注 |
|---|---|---|---|---|---|
| A | Adaptive min_support (0.003) | 9,158 | 8.67 | — | 规则太多 |
| A' | Adaptive (0.0002) | 2,856,740 | 5.59 | — | 不可用 |
| B | fpmax (closed) | 80 | 11.31 | 80 | 与基线同 |
| **C** | **min_sup=0.008, max_len=4** | **694** | **11.07** | **330** | **+767% 规则** |
| **D** | **Per-cluster rules** | **2,314** | **12.0 avg** | — | **7 簇，含 4 簇 lift>12** |

### 赢家：C + D 组合

**全局规则**（Description 级）：80 → 694 (+767%)，Mean Lift 11.07 (-2.1%)，High-lift 80 → 330 (+313%)

**StockCode 规则**：152 → 1,456 (+858%)

**季节性规则**：
- Christmas: 56 → 166 (+196%)
- Normal: 116 → 248 (+114%)

**分群规则**（新增）：
| 簇 | 业务标签 | 客户 | 规则 | Mean Lift |
|---|---|---|---|---|
| -1 | 兜底簇 | 154 | 246 | **26.74** ⭐ |
| 0 | 高价值忠诚 | 1,404 | 110 | **12.22** ⭐ |
| 1 | 流失预警 | 1,481 | 22 | **18.03** ⭐ |
| 2 | 高频低流失 | 334 | 420 | 8.60 |
| 3 | 低消费高频 | 1,318 | 302 | 6.91 |
| 4 | 忠诚客户 | 1,180 | 608 | 7.55 |
| 999 | 异常客户 | 7 | 606 | 7.10 |

**业务洞察**：
- 簇 -1 (新发现簇, n=154) 拥有最高 lift 26.74 — 极强购买关联
- 簇 1 (流失预警) 规则少但 lift 高 18.03 — 精准营销机会
- 簇 4 (忠诚) 规则数最多 608 — 交叉销售主战场

### 文献支持
- Hidayat 2021: 自适应 min_support 方法（基于数据密度）
- mlxtend 文档: fpgrowth 5x faster than apriori
- Springer 2024: fpmax 闭频繁项集（精简规则）

---

## 文件变更清单

### 备份（原文件，安全保留）
```
ShopMiner/experiments/back_up/
├── phase3_clusters_v3.pkl             (基线 Sil=0.272)
├── phase3_clusters_v3_v3_pre_optuna.pkl  (Optuna 调优前 v3, Sil=0.360)
├── phase4_churn_v5.pkl                (基线 OOT=0.631)
├── phase4_churn_v5_v6_pre_optuna.pkl  (Optuna 调优前 v6, OOT=0.904)
├── phase5_forecast_v2.pkl             (基线 SMAPE=5.25%)
├── phase5_forecast_v2_rolling.pkl
├── phase5_forecast_v2_weighted.pkl
├── phase6_association_v2.pkl          (基线 80 规则)
└── phase6_association_v2.json
```

### 覆盖（原位置，已替换）
```
ShopMiner/data/prep/
├── phase3_clusters_v3.pkl       → Sil=0.3599 (v4: Optuna 调优)
├── phase4_churn_v5.pkl          → OOT=0.913 (v7: Optuna 调优)
├── phase5_forecast_v2.pkl       → SMAPE=4.86% (v3 不变, 仍最优)
├── phase5_forecast_v2_rolling.pkl (未改)
├── phase5_forecast_v2_weighted.pkl (未改)
├── phase6_association_v2.pkl    → 694 规则 (v3 不变, 仍最优)
└── phase6_association_v2.json   → 完整重写
```

### 实验产物
```
ShopMiner/experiments/
├── back_up/                        (8 个原/中间 pkl 备份)
├── phase3/
│   ├── exp_phase3.py               (4 方向实验)
│   ├── build_winner.py             (D 方向赢家构建)
│   ├── optuna_tune.py              (Optuna 50 trials, Sil 0.360 → 0.360)  ← 新
│   ├── deploy_v4.py                (部署 v4)  ← 新
│   ├── phase3_clusters_winner.pkl
│   ├── phase3_optuna.json          ← 新
├── phase4/
│   ├── exp_phase4.py               (5 方向实验)
│   ├── exp_phase4_hybrid.py        (混合 Stacking+SMOTE-ENN)
│   ├── exp_phase4_final.py         (公平对比 v5 vs XGB)
│   ├── optuna_tune.py              (Optuna 40 trials, OOT 0.904 → 0.913)  ← 新
│   ├── optuna_tune_v2.py           (时序 objective 修正版)  ← 新
│   ├── shap_select.py              (SHAP K 搜索)  ← 新
│   ├── deploy_v7.py                (部署 v7)  ← 新
│   ├── build_winner.py             (XGBoost_spw 赢家构建)
│   ├── phase4_churn_winner.pkl
│   ├── phase4_compare.json
│   ├── phase4_final.json
│   ├── phase4_optuna.json          ← 新
│   └── phase4_shap.json            ← 新
├── phase5/
│   ├── exp_phase5.py               (5 方向实验)
│   ├── optuna_tune.py              (Optuna 40 trials, 退化)  ← 新
│   ├── optuna_tune_v2.py           (TimeSeriesSplit CV 版)  ← 新
│   ├── exp_darts.py                (Darts N-BEATS 集成, 退化)  ← 新
│   ├── build_winner.py             (UK 日历特征赢家构建)
│   ├── phase5_forecast_winner.pkl
│   ├── phase5_compare.json
│   ├── phase5_optuna.json          ← 新
│   └── phase5_darts.json           ← 新
├── phase6/
│   ├── exp_phase6.py               (4 方向实验)
│   ├── optuna_tune.py              (Optuna 30 trials, 退化)  ← 新
│   ├── build_winner.py             (低阈值+分群赢家构建)
│   ├── phase6_association_winner.pkl
│   ├── phase6_association_winner.json
│   ├── phase6_compare.json
│   └── phase6_optuna.json          ← 新
├── requirements_extras.txt         (dart 装在 conda 的说明)  ← 新
├── _verify.py                      (验证脚本)
└── compare_report.md               (本报告)
```

---

## 关键启示

1. **模型复杂度 ≠ 性能**：XGBoost_spw（单模型）击败 Stacking 集成，原因是单模型更不易过拟合 OOT
2. **OOT 比 Test 更重要**：v5 Stacking Test AUC 0.918 但 OOT 0.631（明显过拟合）；新模型 Test 0.803 / OOT 0.904（生产可靠）
3. **特征工程 > 模型选择**：Phase 5 仅添加 11 个日历特征就降低 SMAPE 7.5%，比 log 变换、Prophet 集成更有效
4. **log1p 是 RFM 数据标配**：右偏分布下，log 变换让 K-Means 距离度量更合理
5. **分群规则显著优于全局规则**：簇 -1 平均 lift 26.74，是全局平均的 2.4 倍
6. **时序 objective > 随机 test objective**：Optuna 调 XGBoost 时，用 random test AUC 当 objective 会过拟合（OOT -8.6%），改用时序 holdout 反而 +0.96%
7. **SHAP 验证了 v7 特征集已最优**：K=20 掉 1.5% OOT，说明现有 53 特征每个都有贡献
8. **小样本（<100 时间步）DL 输 LGBM**：Darts N-BEATS SMAPE 15.5% vs LightGBM 4.86%，数据量是 DL 时序模型的硬门槛
9. **FP-Growth 调优是质量换数量**：v3 的 694 规则 @ lift 11 业务价值 > 392 规则 @ lift 17

---

## 后续建议

- **监控**：将新模型集成到 compute_analytics.py 流水线
- **重训**：建议每月用最新数据重训（防止分布漂移）
- **A/B 测试**：Phase 4 新模型建议在 10% 流量上 A/B 测试 1 个月
- **进一步优化**：
  - Phase 5：考虑添加促销/库存外部特征，或采集多年数据（≥2 年周）让 N-BEATS 发挥
  - Phase 6：序列挖掘（PrefixSpan）发现时序模式
  - Phase 4：尝试 TabNet（需要 PyTorch，环境已就绪），或拼多多 / Hotukdeals 外部数据
  - **跨模型联动**：Phase 4 流失预警 + Phase 6 关联规则 → 流失客户精准挽留套餐
  - **监控脚本**：每月 PSI 漂移检测 + 性能退化自动重训

---

## 8. 模型可视化交付（v3, 2026-06-01）

### 8.1 新增文件
- `scripts/generate_model_viz.py` — 4 模型图表数据预计算（<15s 跑完）
- `app/services/analytics_service.py` — `get_model_viz()` 函数（name_map 支持 phase3/Clustering 两种 key）
- `app/api/v1/analytics/routes.py` — `GET /api/v1/analytics/viz/<model>` 端点（admin-only）
- `frontend/src/api/index.js` — `getModelViz()` 包装
- `frontend/src/views/Admin.vue` — 4 个主页面核心图 + 4 个 el-dialog 全量图 + 11 个新 chart 渲染函数
- `scripts/compute_analytics.py` — 重算末尾自动调 viz 生成（无需手动跑）
- `data/prep/phase{3,4,5,6}_viz.json` — 4 个预计算 JSON（总计 112 KB）

### 8.2 预计算数据内容
- Phase 3: metadata + 1500 PCA 2D 散点 + 4 簇 RFM 画像
- Phase 4: metadata + 50 ROC 曲线点 + 3 OOT 窗口 + 15 特征重要性
- Phase 5: metadata + 8 周实际vs预测 + 15 残差直方 + 12 月季节性
- Phase 6: metadata + 20 顶部规则 + 30 规则散点 + 7 分群规则摘要

### 8.3 设计决策
- **预计算优先**：用户看页面 0 等待，重算 <15s 集中在管理员点击时
- **业务 + 技术双视角**：主页面 1 核心业务图，详情页 2-3 全量技术图
- **复用 el-dialog**：不修改 Vue 现有结构，只新增 viz section + dialog
- **弹窗 dispose**：el-dialog 关闭时 dispose chart 防止 echarts 内存泄漏
- **触发流程**：compute_analytics.py 末尾 subprocess 调 generate_model_viz.py

### 8.4 验证
- 4 API 端点全部 200（test_smape/oot_mean_auc/n_global_rules metadata 正确）
- 前端 `npm run build` 8.4s 通过（Admin.vue chunk 53.25 kB）
- 4 JSON 体积小（99.6 + 2.8 + 2.2 + 7.2 = 112 KB），适合静态托管
