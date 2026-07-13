# ShopMiner — 智能电商平台 · 数据挖掘与质量保障

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-000)](https://flask.palletsprojects.com)
[![Vue](https://img.shields.io/badge/Vue-3-4FC08D)](https://vuejs.org)
[![Test Suite](https://github.com/yangrs1/ShopMiner/actions/workflows/test.yml/badge.svg)](https://github.com/yangrs1/ShopMiner/actions/workflows/test.yml)
[![Coverage](https://img.shields.io/badge/Coverage-82%25-brightgreen)]()
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

> 集成 RFM 客户分群、销量预测、流失预警、关联规则推荐的智能电商平台。全栈自研（Flask + Vue 3），配备完整的自动化测试体系。

---

## 技术栈

| 层级 | 技术 |
|:-----|:-----|
| 前端 | Vue 3 + Element Plus + ECharts + Pinia |
| 后端 | Flask 3.0 + SQLAlchemy + JWT |
| 数据库 | PostgreSQL 16（生产）/ SQLite（测试）|
| 数据挖掘 | Scikit-learn、LightGBM、Prophet、自实现 Apriori |
| 测试 | pytest + Playwright + Allure + GitHub Actions |

## 数据挖掘功能

| 功能 | 算法 | 说明 |
|:-----|:------|:------|
| RFM 客户分群 | 决策表（125 种组合覆盖） | 按消费时间/频率/金额分 5 个等级 |
| 销量预测 | Prophet 时序模型 | 按日/周/月粒度预测销量趋势 |
| 客户流失预警 | LightGBM（AUC 0.913） | 预测 7/30 天流失概率 |
| 商品关联规则 | 自实现 Apriori | 挖掘商品组合购买规律 |

## 快速开始

```bash
# 1. 后端
pip install -r requirements.txt
cp .env.example .env  # 填入配置
flask db upgrade
python scripts/seed_demo_data.py
python run.py

# 2. 前端
cd frontend
npm install
npm run dev
```

## 测试体系

```bash
# 运行后端测试
python -m pytest tests/unit/ tests/api/ -v

# 运行 Web UI 测试
cd tests/web && pytest -v

# 查看覆盖率
pytest --cov=app --cov-report=html
```

| 类型 | 工具 | 范围 |
|------|------|------|
| 单元测试 | pytest | RFM 分群算法、模型方法、业务服务 |
| API 测试 | pytest + requests | 全部业务端点 |
| UI 测试 | Playwright | 核心用户界面交互 |
| 安全测试 | pytest | SQL 注入、XSS 检测 |
| 边界测试 | pytest | 价格/分页/认证/充值边界 |
| 数据驱动 | YAML + Faker | 10 个 YAML 文件，支持动态数据 |

## 项目结构

```
ShopMiner/
├── app/             # Flask 后端（API / 模型 / 服务 / 任务）
├── frontend/        # Vue 3 前端
├── tests/           # 测试套件（API / 单元 / Web / YAML 数据）
│   ├── api/         # 24 个 API 测试文件
│   ├── unit/        # 7 个单元测试文件
│   ├── web/         # 6 个 Playwright UI 测试文件
│   └── data/yaml/   # 9 个 YAML 数据驱动文件
├── scripts/         # 数据挖掘 Pipeline
└── docker-compose.yml
```

## 许可证

MIT
