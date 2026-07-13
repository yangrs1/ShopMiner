from sqlalchemy import func
from datetime import datetime, timezone
import json
from app.models.order import Order, OrderItem
from app.models.user import User
from app.models.product import Product
from app.models.analytics import (
    RFMAnalysis, SalesPrediction, AssociationRule,
    ChurnPrediction, UserBehavior, ModelMetric,
)
from app.extensions import db
import os
import logging

logger = logging.getLogger(__name__)


def require_admin(user_id):
    user = db.session.get(User, user_id)
    if not user or user.role != "admin":
        return None
    return user


def get_dashboard_stats():
    total_users = User.query.count()
    total_orders = Order.query.count()
    total_revenue = db.session.query(func.sum(Order.total_amount)).filter(
        Order.status.in_([Order.STATUS_PAID, Order.STATUS_SHIPPED, Order.STATUS_DELIVERED])
    ).scalar() or 0
    paid_orders = Order.query.filter(Order.status != Order.STATUS_CANCELLED).count()
    segments = db.session.query(
        RFMAnalysis.segment, func.count(RFMAnalysis.id)
    ).group_by(RFMAnalysis.segment).all()
    risk_count = ChurnPrediction.query.filter_by(is_churn_risk=True).count()

    # New algorithm metrics
    clustering_k = ModelMetric.query.filter_by(model_name="Clustering", metric_name="K").first()
    churn_auc = ModelMetric.query.filter_by(model_name="Churn", metric_name="test_auc").first()
    forecast_smape = ModelMetric.query.filter_by(model_name="SalesForecast", metric_name="best_smape").first()
    assoc_count = ModelMetric.query.filter_by(model_name="Association", metric_name="global_rules_count").first()

    return {
        "total_users": total_users,
        "total_products": Product.query.filter_by(is_active=True).count(),
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "paid_orders": paid_orders,
        "churn_risk_count": risk_count,
        "rfm_segments": [{"segment": s[0], "count": s[1]} for s in segments],
        "clustering_k": int(clustering_k.metric_value) if clustering_k else 0,
        "churn_auc": float(churn_auc.metric_value) if churn_auc else 0,
        "forecast_smape": float(forecast_smape.metric_value) if forecast_smape else 0,
        "association_rules_count": int(assoc_count.metric_value) if assoc_count else 0,
    }


def get_rfm_summary():
    records = RFMAnalysis.query.all()
    if not records:
        return {"segments": []}
    
    # Aggregate by segment
    seg_agg = {}
    for r in records:
        if r.segment not in seg_agg:
            seg_agg[r.segment] = {"count": 0, "recency_sum": 0, "frequency_sum": 0, "monetary_sum": 0}
        agg = seg_agg[r.segment]
        agg["count"] += 1
        agg["recency_sum"] += r.recency
        agg["frequency_sum"] += r.frequency
        agg["monetary_sum"] += r.monetary
    
    segments = []
    for seg, agg in seg_agg.items():
        segments.append({
            "segment": seg,
            "count": agg["count"],
            "avg_recency": round(agg["recency_sum"] / agg["count"], 1),
            "avg_frequency": round(agg["frequency_sum"] / agg["count"], 1),
            "avg_monetary": round(agg["monetary_sum"] / agg["count"], 1),
        })
    
    return {"segments": segments}


# [GAP: missing-test] analytics_service.get_sales_trend() has no unit test
def get_sales_trend():
    return db.session.query(
        func.date(Order.created_at).label("date"),
        func.sum(Order.total_amount).label("amount"),
        func.count(Order.id).label("count"),
    ).filter(
        Order.status.in_([Order.STATUS_PAID, Order.STATUS_SHIPPED, Order.STATUS_DELIVERED])
    ).group_by(func.date(Order.created_at)).order_by(func.date(Order.created_at)).all()


# [GAP: missing-test] analytics_service.get_sales_prediction() has no unit test
def get_sales_prediction():
    preds = SalesPrediction.query.order_by(SalesPrediction.pred_date).all()
    historical = db.session.query(
        func.strftime("%Y-%m", Order.created_at).label("month"),
        func.sum(Order.total_amount).label("amount"),
    ).filter(
        Order.status.in_([Order.STATUS_PAID, Order.STATUS_SHIPPED, Order.STATUS_DELIVERED])
    ).group_by(func.strftime("%Y-%m", Order.created_at)).order_by("month").all()

    # 按月份汇总周度预测数据，确保与历史数据粒度一致
    from collections import defaultdict
    pred_by_month = defaultdict(lambda: {"amount": 0.0, "upper": 0.0, "lower": 0.0, "count": 0})
    for p in preds:
        month_key = p.pred_date.strftime("%Y-%m") if hasattr(p.pred_date, "strftime") else str(p.pred_date)[:7]
        pred_by_month[month_key]["amount"] += p.pred_amount or 0
        pred_by_month[month_key]["upper"] += p.pred_upper or 0
        pred_by_month[month_key]["lower"] += p.pred_lower or 0
        pred_by_month[month_key]["count"] += 1
    monthly_preds = []
    for month_key in sorted(pred_by_month.keys()):
        d = pred_by_month[month_key]
        monthly_preds.append({
            "month": month_key,
            "pred_amount": d["amount"],
            "pred_upper": d["upper"],
            "pred_lower": d["lower"],
        })
    return historical, monthly_preds


def get_association_rules(page=1, per_page=50):
    return AssociationRule.query.order_by(AssociationRule.lift.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )


# [GAP: missing-test] analytics_service.get_product_recommendations() has no unit test
def get_product_recommendations(product_id, limit=6):
    rules = AssociationRule.query.filter_by(product_id=product_id).order_by(
        AssociationRule.lift.desc()
    ).limit(limit).all()

    recommendations = []
    seen = set()
    for r in rules:
        if r.consequent_id and r.consequent_id not in seen:
            seen.add(r.consequent_id)
            product = db.session.get(Product, r.consequent_id)
            if product and product.is_active:
                recommendations.append({
                    "product": product.to_dict(),
                    "support": r.support,
                    "confidence": r.confidence,
                    "lift": r.lift,
                })
    return recommendations


def get_churn_list(page=1, per_page=20, risk_only=False):
    query = ChurnPrediction.query
    if risk_only:
        query = query.filter_by(is_churn_risk=True)

    pagination = query.order_by(ChurnPrediction.churn_prob.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    user_ids = [c.user_id for c in pagination.items]
    users = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}
    rfm_records = {
        r.user_id: r for r in RFMAnalysis.query.filter(RFMAnalysis.user_id.in_(user_ids)).all()
    }

    # 使用模型最优阈值（从ModelMetric读取，默认0.5）
    threshold_metric = ModelMetric.query.filter_by(
        model_name="Churn", metric_name="optimal_threshold"
    ).first()
    OPTIMAL_THRESHOLD = float(threshold_metric.metric_value) if threshold_metric else 0.5

    result = []
    for c in pagination.items:
        u = users.get(c.user_id)
        rfm = rfm_records.get(c.user_id)
        item = c.to_dict()
        item["email"] = u.email if u else ""
        item["user_name"] = f"{u.first_name} {u.last_name}" if u else ""
        item["segment"] = rfm.segment if rfm else ""
        item["churn_probability"] = item.pop("churn_prob", 0)
        prob = item["churn_probability"]
        if prob >= 0.85:
            item["risk_level"] = "high"
        elif prob >= OPTIMAL_THRESHOLD:
            item["risk_level"] = "medium"
        else:
            item["risk_level"] = "low"
        item["prediction_date"] = c.created_at.strftime("%Y-%m-%d") if c.created_at else ""
        result.append(item)

    # 全量统计摘要
    summary = db.session.query(
        db.case(
            (ChurnPrediction.churn_prob >= 0.85, "high"),
            (ChurnPrediction.churn_prob >= OPTIMAL_THRESHOLD, "medium"),
            else_="low"
        ).label("level"),
        db.func.count(ChurnPrediction.id)
    ).group_by("level").all()
    summary_map = {s[0]: s[1] for s in summary}
    high_count = summary_map.get("high", 0)
    medium_count = summary_map.get("medium", 0)
    low_count = summary_map.get("low", 0)
    resolved_count = ChurnPrediction.query.filter_by(status="resolved").count()

    return result, pagination.total, pagination.pages, {
        "high": high_count,
        "medium": medium_count,
        "low": low_count,
        "resolved": resolved_count,
        "total_risk": ChurnPrediction.query.filter_by(is_churn_risk=True).count(),
    }


def get_churn_importance():
    """获取特征重要性（从ModelMetric读取真实重要性分数）"""
    metrics = ModelMetric.query.filter(
        ModelMetric.model_name == "Churn",
        ModelMetric.metric_name.like("feature_importance_%"),
    ).order_by(ModelMetric.metric_value.desc()).all()

    feature_counts = []
    for m in metrics:
        fname = m.metric_name.replace("feature_importance_", "")
        feature_counts.append({
            "feature": fname,
            "count": int(m.metric_value),
        })

    total_risk = ChurnPrediction.query.filter_by(is_churn_risk=True).count()
    total_all = ChurnPrediction.query.count()

    return {
        "feature_counts": feature_counts,
        "total_risk": total_risk,
        "total_all": total_all,
    }


# [GAP: missing-test] analytics_service.get_user_rfm() has no unit test
def get_user_rfm(user_id):
    rfm = RFMAnalysis.query.filter_by(user_id=user_id).first()
    if not rfm:
        return None

    all_records = RFMAnalysis.query.all()
    avg_r = sum(r.r_score for r in all_records) / len(all_records) if all_records else 0
    avg_f = sum(r.f_score for r in all_records) / len(all_records) if all_records else 0
    avg_m = sum(r.m_score for r in all_records) / len(all_records) if all_records else 0

    segment_dist = {}
    for r in all_records:
        segment_dist[r.segment] = segment_dist.get(r.segment, 0) + 1
    total_rfm = len(all_records)

    advice = {
        "高价值客户": "您是我们的核心客户！感谢您的持续支持，我们将为您提供专属优惠。",
        "潜力客户": "您有很高的消费潜力！看看我们的新品推荐，发现更多好物。",
        "一般客户": "感谢您的光临！参与我们的会员活动可享受更多优惠。",
        "流失预警": "好久不见！我们为您准备了回归礼包，欢迎回来看看~",
        "低价值客户": "欢迎来到 ShopMiner！新用户可享受首单优惠。",
    }

    return {
        "my_rfm": rfm.to_dict(),
        "my_segment": rfm.segment,
        "my_segment_advice": advice.get(rfm.segment, ""),
        "radar": {
            "my_scores": [rfm.r_score, rfm.f_score, rfm.m_score],
            "avg_scores": [round(avg_r, 2), round(avg_f, 2), round(avg_m, 2)],
        },
        "segment_distribution": [
            {"name": seg, "value": cnt, "percent": round(cnt / total_rfm * 100, 1)}
            for seg, cnt in segment_dist.items()
        ] if total_rfm > 0 else [],
    }


# [GAP: missing-test] analytics_service.get_user_trend() has no unit test
def get_user_trend(user_id):
    return db.session.query(
        func.strftime("%Y-%m", Order.created_at).label("month"),
        func.sum(Order.total_amount).label("amount"),
        func.count(Order.id).label("count"),
    ).filter(
        Order.user_id == user_id,
        Order.status.in_([Order.STATUS_PAID, Order.STATUS_SHIPPED, Order.STATUS_DELIVERED])
    ).group_by(func.strftime("%Y-%m", Order.created_at)).order_by("month").all()


# [GAP: missing-test] analytics_service.get_user_category_preference() has no unit test
def get_user_category_preference(user_id):
    order_ids = [o.id for o in Order.query.filter_by(user_id=user_id).all()]
    if not order_ids:
        return []

    items = OrderItem.query.filter(OrderItem.order_id.in_(order_ids)).all()
    product_ids = list(set(it.product_id for it in items))
    products = {p.id: p for p in Product.query.filter(Product.id.in_(product_ids)).all()}

    category_amount = {}
    category_count = {}
    for it in items:
        p = products.get(it.product_id)
        if not p:
            continue
        cat = p.category_name or "其他"
        category_amount[cat] = category_amount.get(cat, 0) + it.unit_price * it.quantity
        category_count[cat] = category_count.get(cat, 0) + 1

    total_amount = sum(category_amount.values())
    result = []
    for cat in sorted(category_amount, key=category_amount.get, reverse=True):
        result.append({
            "category": cat,
            "amount": category_amount[cat],
            "count": category_count.get(cat, 0),
            "percent": round(category_amount[cat] / total_amount * 100, 1) if total_amount > 0 else 0,
        })
    return result


# [GAP: missing-test] analytics_service.get_model_metrics() has no unit test
def get_model_metrics(model_name=None):
    query = ModelMetric.query
    if model_name:
        query = query.filter_by(model_name=model_name)

    metrics = query.order_by(ModelMetric.model_name, ModelMetric.id).all()
    grouped = {}
    for m in metrics:
        if m.model_name not in grouped:
            grouped[m.model_name] = []
        grouped[m.model_name].append(m.to_dict())
    return grouped


def get_hot_products(category=None, limit=6):
    """品类热门推荐：按销量排序，无关联规则时的fallback"""
    query = Product.query.filter_by(is_active=True)
    if category:
        query = query.filter_by(category_name=category)

    products = query.order_by(Product.created_at.desc()).limit(limit).all()
    return [p.to_dict() for p in products]


def trigger_recompute():
    """Trigger Celery async recompute of analytics."""
    try:
        from app.tasks import compute_analytics_task
    except (ImportError, ModuleNotFoundError):
        return {"status": "error", "message": "Celery is not installed in this environment"}
    try:
        task = compute_analytics_task.delay()
        return {"status": "started", "task_id": task.id}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_last_compute_time():
    metric = ModelMetric.query.order_by(ModelMetric.created_at.desc()).first()
    return metric.created_at.isoformat() if metric else None


def update_user_rfm(user_id):
    """轻量级单用户 RFM 更新，支付成功后自动触发"""
    today = datetime.now(timezone.utc).date()

    orders = Order.query.filter(
        Order.user_id == user_id,
        Order.status.in_([Order.STATUS_PAID, Order.STATUS_SHIPPED, Order.STATUS_DELIVERED])
    ).order_by(Order.created_at.desc()).all()

    if not orders:
        return

    last_order_date = orders[0].created_at
    if isinstance(last_order_date, datetime):
        last_order_date = last_order_date.date()
    recency = (today - last_order_date).days

    frequency = len(orders)
    monetary = sum(o.total_amount for o in orders)

    r_score = 5 if recency <= 30 else 4 if recency <= 90 else 3 if recency <= 180 else 2 if recency <= 365 else 1
    f_score = 5 if frequency >= 20 else 4 if frequency >= 10 else 3 if frequency >= 5 else 2 if frequency >= 2 else 1
    m_score = 5 if monetary >= 500000 else 4 if monetary >= 200000 else 3 if monetary >= 50000 else 2 if monetary >= 10000 else 1

    segment = _compute_segment(r_score, f_score, m_score)

    existing = RFMAnalysis.query.filter_by(user_id=user_id).first()
    if existing:
        existing.recency = recency
        existing.frequency = frequency
        existing.monetary = monetary
        existing.r_score = r_score
        existing.f_score = f_score
        existing.m_score = m_score
        existing.rfm_score = r_score + f_score + m_score
        existing.segment = segment
    else:
        db.session.add(RFMAnalysis(
            user_id=user_id, recency=recency, frequency=frequency,
            monetary=monetary, r_score=r_score, f_score=f_score,
            m_score=m_score, rfm_score=r_score + f_score + m_score,
            segment=segment,
        ))
    db.session.commit()


def _compute_segment(r, f, m):
    if r >= 4 and f >= 4 and m >= 4:
        return "高价值客户"
    if r >= 3 and f >= 3 and m >= 3:
        return "潜力客户"
    if r <= 2 and f <= 2 and m <= 2:
        return "低价值客户"
    if r <= 2 and f >= 3:
        return "流失预警"
    return "一般客户"


def get_churn_trend():
    """获取流失风险分布：按概率区间统计用户数"""
    from sqlalchemy import func as sa_func

    total = ChurnPrediction.query.count()

    buckets = [
        ("0-20%", 0, 0.2),
        ("20-40%", 0.2, 0.4),
        ("40-60%", 0.4, 0.6),
        ("60-80%", 0.6, 0.8),
        ("80-100%", 0.8, 1.0),
    ]

    records = ChurnPrediction.query.all()
    bucket_counts = {b[0]: 0 for b in buckets}
    for r in records:
        p = r.churn_prob
        for label, lo, hi in buckets:
            if lo <= p < hi:
                bucket_counts[label] += 1
                break
        if p >= 1.0:
            bucket_counts["80-100%"] += 1

    result = []
    for label, lo, hi in buckets:
        count = bucket_counts[label]
        result.append({
            "bucket": label,
            "count": count,
            "rate": round(count / total * 100, 1) if total > 0 else 0,
        })

    return result


# [GAP: missing-test] analytics_service.get_sales_heatmap() has no unit test
def get_sales_heatmap():
    """获取销售热力图数据：按星期几和月份聚合"""
    from sqlalchemy import func as sa_func
    results = db.session.query(
        sa_func.strftime("%Y-%m", Order.created_at).label("month"),
        sa_func.strftime("%w", Order.created_at).label("day_of_week"),
        sa_func.sum(Order.total_amount).label("amount"),
        sa_func.count(Order.id).label("count"),
    ).filter(
        Order.status.in_([Order.STATUS_PAID, Order.STATUS_SHIPPED, Order.STATUS_DELIVERED])
    ).group_by("month", "day_of_week").order_by("month", "day_of_week").all()

    day_names = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]
    data_map = {}
    for r in results:
        if r.month not in data_map:
            data_map[r.month] = {}
        data_map[r.month][int(r.day_of_week)] = {
            "amount": r.amount / 100,
            "count": r.count,
        }

    months = sorted(data_map.keys())[-6:]
    series_data = []
    for mi, m in enumerate(months):
        for di in range(7):
            val = data_map.get(m, {}).get(di, {}).get("amount", 0)
            series_data.append([di, mi, round(val, 0)])

    return {
        "months": months,
        "days": day_names,
        "data": series_data,
    }


# [GAP: missing-test] analytics_service.get_prediction_metrics() has no unit test
def get_prediction_metrics():
    """获取预测准确度指标"""
    from app.models.analytics import ModelMetric
    # New algorithm models
    lgbm_metrics = ModelMetric.query.filter_by(model_name="SalesForecast").order_by(ModelMetric.id).all()
    # Legacy models (backward compatible)
    prophet_metrics = ModelMetric.query.filter_by(model_name="Prophet").order_by(ModelMetric.id).all()
    sarima_metrics = ModelMetric.query.filter_by(model_name="SARIMA").order_by(ModelMetric.id).all()

    def extract(metrics):
        result = {}
        for m in metrics:
            name = m.metric_name
            result[name] = {"value": m.metric_value, "detail": m.detail}
        return result

    data = {}
    if lgbm_metrics:
        data["LightGBM_Weekly"] = extract(lgbm_metrics)
    if prophet_metrics:
        data["Prophet"] = extract(prophet_metrics)
    if sarima_metrics:
        data["SARIMA"] = extract(sarima_metrics)
    return data


# [GAP: missing-test] analytics_service.get_model_viz() has no unit test
def get_model_viz(model_name):
    """读取预计算的图表数据 (data/prep/phase*_viz.json)

    model_name 支持 phase3/4/5/6 或 Clustering/Churn/SalesForecast/Association
    """
    name_map = {
        "phase3": "phase3",
        "phase4": "phase4",
        "phase5": "phase5",
        "phase6": "phase6",
        "Clustering": "phase3",
        "Churn": "phase4",
        "SalesForecast": "phase5",
        "Association": "phase6",
    }
    file_key = name_map.get(model_name, model_name)
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    viz_path = os.path.join(project_root, "data", "prep", f"{file_key}_viz.json")

    if not os.path.exists(viz_path):
        return None
    try:
        with open(viz_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.exception(f"Failed to load viz json: {e}")
        return None


# [GAP: missing-test] analytics_service.update_churn_status() has no unit test
def update_churn_status(churn_id, status):
    """更新流失预警处理状态"""
    churn = db.session.get(ChurnPrediction, churn_id)
    if not churn:
        return None
    if status not in ("pending", "contacted", "resolved"):
        return None
    churn.status = status
    db.session.commit()
    return churn.to_dict()
