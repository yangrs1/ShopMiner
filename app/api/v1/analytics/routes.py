from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.services import analytics_service
from app.services.auth_service import get_user_by_id
from app.models.analytics import (
    RFMAnalysis, SalesPrediction, AssociationRule,
    ChurnPrediction, ModelMetric, Review
)
from app.models.product import Product

analytics_bp = Blueprint("analytics", __name__)


def _require_admin():
    user_id = int(get_jwt_identity())
    return analytics_service.require_admin(user_id)


def _get_current_user():
    try:
        return get_user_by_id(int(get_jwt_identity()))
    except Exception:
        return None


# ============================================================
# Admin Dashboard
# ============================================================
@analytics_bp.route("/analytics/dashboard", methods=["GET"])
@jwt_required()
def dashboard():
    if not _require_admin():
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    return jsonify({"code": 200, "message": "success", "data": analytics_service.get_dashboard_stats()}), 200


# ============================================================
# RFM
# ============================================================
@analytics_bp.route("/analytics/rfm/summary", methods=["GET"])
@jwt_required()
def rfm_summary():
    if not _require_admin():
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    return jsonify({"code": 200, "message": "success", "data": analytics_service.get_rfm_summary()}), 200


@analytics_bp.route("/analytics/clustering/detail", methods=["GET"])
@jwt_required()
def clustering_detail():
    """获取客户分群详细信息（基于新K-Means算法）"""
    if not _require_admin():
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    from app.models.analytics import ModelMetric
    # Get clustering metrics
    metrics = ModelMetric.query.filter_by(model_name="Clustering").all()
    metrics_dict = {m.metric_name: {"value": m.metric_value, "detail": m.detail} for m in metrics}

    # Get RFM segment distribution
    segments = analytics_service.get_rfm_summary()

    return jsonify({
        "code": 200, "message": "success",
        "data": {
            "metrics": metrics_dict,
            "segments": segments,
        },
    }), 200


# ============================================================
# Sales Trend & Prediction
# ============================================================
@analytics_bp.route("/analytics/sales/trend", methods=["GET"])
@jwt_required()
def sales_trend():
    if not _require_admin():
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    rows = analytics_service.get_sales_trend()
    return jsonify({
        "code": 200, "message": "success",
        "data": [{"date": str(r.date), "amount": r.amount, "count": r.count} for r in rows],
    }), 200


@analytics_bp.route("/analytics/sales/prediction", methods=["GET"])
@jwt_required()
def sales_prediction():
    if not _require_admin():
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    historical, preds = analytics_service.get_sales_prediction()

    return jsonify({
        "code": 200, "message": "success",
        "data": {
            "historical": [{"month": h[0], "amount": h[1]} for h in historical],
            "predictions": preds,
        },
    }), 200


# ============================================================
# Association Rules
# ============================================================
@analytics_bp.route("/analytics/association/list", methods=["GET"])
@jwt_required()
def association_list():
    if not _require_admin():
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 50, type=int)
    pagination = analytics_service.get_association_rules(page, per_page)

    return jsonify({
        "code": 200, "message": "success",
        "data": {
            "rules": [r.to_dict() for r in pagination.items],
            "total": pagination.total, "pages": pagination.pages, "page": page,
        },
    }), 200


@analytics_bp.route("/analytics/association/product/<int:product_id>", methods=["GET"])
def association_for_product(product_id):
    recommendations = analytics_service.get_product_recommendations(product_id)
    return jsonify({
        "code": 200, "message": "success",
        "data": {"product_id": product_id, "recommendations": recommendations},
    }), 200


# ============================================================
# Churn Prediction
# ============================================================
@analytics_bp.route("/analytics/churn/list", methods=["GET"])
@jwt_required()
def churn_list():
    if not _require_admin():
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    risk_only = request.args.get("risk_only", "0") == "1"

    result, total, pages, summary = analytics_service.get_churn_list(page, per_page, risk_only)
    return jsonify({
        "code": 200, "message": "success",
        "data": {"predictions": result, "total": total, "pages": pages, "page": page, "summary": summary},
    }), 200


@analytics_bp.route("/analytics/churn/importance", methods=["GET"])
@jwt_required()
def churn_importance():
    if not _require_admin():
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    return jsonify({"code": 200, "message": "success", "data": analytics_service.get_churn_importance()}), 200


# ============================================================
# User Personal Analytics
# ============================================================
@analytics_bp.route("/analytics/user/rfm", methods=["GET"])
@jwt_required()
def user_rfm():
    user = _get_current_user()
    if not user:
        return jsonify({"code": 401, "message": "Unauthorized"}), 401

    data = analytics_service.get_user_rfm(user.id)
    if not data:
        # 新用户冷启动：返回默认分群
        return jsonify({
            "code": 200,
            "message": "success",
            "data": {
                "my_rfm": None,
                "my_segment": "新用户",
                "my_segment_advice": "欢迎来到 ShopMiner！完成首笔订单即可获得专属消费报告。",
                "radar": {"my_scores": [0, 0, 0], "avg_scores": [0, 0, 0]},
                "segment_distribution": [],
            },
        }), 200

    return jsonify({"code": 200, "message": "success", "data": data}), 200


@analytics_bp.route("/analytics/user/trend", methods=["GET"])
@jwt_required()
def user_trend():
    user = _get_current_user()
    if not user:
        return jsonify({"code": 401, "message": "Unauthorized"}), 401

    rows = analytics_service.get_user_trend(user.id)
    return jsonify({
        "code": 200, "message": "success",
        "data": [{"month": m[0], "amount": m[1], "count": m[2]} for m in rows],
    }), 200


@analytics_bp.route("/analytics/user/category-preference", methods=["GET"])
@jwt_required()
def user_category_preference():
    user = _get_current_user()
    if not user:
        return jsonify({"code": 401, "message": "Unauthorized"}), 401

    return jsonify({"code": 200, "message": "success", "data": analytics_service.get_user_category_preference(user.id)}), 200


# ============================================================
# Model Metrics
# ============================================================
@analytics_bp.route("/analytics/metrics", methods=["GET"])
@jwt_required()
def model_metrics():
    if not _require_admin():
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    model_name = request.args.get("model", None)
    return jsonify({"code": 200, "message": "success", "data": analytics_service.get_model_metrics(model_name)}), 200


# ============================================================
# Hot Products (fallback for new users)
# ============================================================
@analytics_bp.route("/analytics/products/hot", methods=["GET"])
def hot_products():
    category = request.args.get("category", None)
    limit = request.args.get("limit", 6, type=int)
    products = analytics_service.get_hot_products(category, limit)
    return jsonify({"code": 200, "message": "success", "data": {"products": products}}), 200


# ============================================================
# Admin Recompute
# ============================================================
@analytics_bp.route("/analytics/admin/recompute", methods=["POST"])
@jwt_required()
def admin_recompute():
    if not _require_admin():
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    result = analytics_service.trigger_recompute()
    return jsonify({"code": 200, "message": "success", "data": result}), 200


# ============================================================
# Task Status
# ============================================================
@analytics_bp.route("/analytics/admin/task-status/<task_id>", methods=["GET"])
@jwt_required()
def task_status(task_id):
    """Query the status of a Celery task by ID."""
    if not _require_admin():
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    from celery.result import AsyncResult
    from app.celery_app import celery as celery_app

    result = AsyncResult(task_id, app=celery_app)
    response_data = {
        "task_id": task_id,
        "status": result.state,
    }
    if result.state == "SUCCESS":
        response_data["result"] = result.result
    elif result.state == "FAILURE":
        response_data["error"] = str(result.result)

    return jsonify({"code": 200, "message": "success", "data": response_data}), 200


# ============================================================
# Review Endpoints
# ============================================================
@analytics_bp.route("/reviews/product/<int:product_id>", methods=["GET"])
def get_product_reviews(product_id):
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 10, type=int)
    pagination = Review.query.filter_by(product_id=product_id).order_by(
        Review.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)
    avg_rating = db.session.query(db.func.avg(Review.rating)).filter_by(
        product_id=product_id
    ).scalar() or 0
    return jsonify({
        "code": 200, "message": "success",
        "data": {
            "reviews": [r.to_dict() for r in pagination.items],
            "avg_rating": round(avg_rating, 1),
            "total": pagination.total,
            "pages": pagination.pages,
        },
    }), 200


@analytics_bp.route("/reviews", methods=["POST"])
@jwt_required()
def create_review():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    product_id = data.get("product_id")
    rating = data.get("rating")
    content = data.get("content", "")

    if not product_id or not rating:
        return jsonify({"code": 400, "message": "product_id and rating are required"}), 400

    if rating < 1 or rating > 5:
        return jsonify({"code": 400, "message": "Rating must be 1-5"}), 400

    existing = Review.query.filter_by(user_id=user_id, product_id=product_id).first()
    if existing:
        existing.rating = rating
        existing.content = content
        db.session.commit()
        return jsonify({"code": 200, "message": "Review updated", "data": existing.to_dict()}), 200

    review = Review(user_id=user_id, product_id=product_id, rating=rating, content=content)
    db.session.add(review)
    db.session.commit()
    return jsonify({"code": 201, "message": "Review created", "data": review.to_dict()}), 201


@analytics_bp.route("/analytics/admin/last-compute-time", methods=["GET"])
@jwt_required()
def last_compute_time():
    if not _require_admin():
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    time_str = analytics_service.get_last_compute_time()
    return jsonify({"code": 200, "message": "success", "data": {"last_compute_time": time_str}}), 200


# ============================================================
# Churn Status Update
# ============================================================
@analytics_bp.route("/analytics/churn/<int:churn_id>/status", methods=["PUT"])
@jwt_required()
def update_churn_status(churn_id):
    if not _require_admin():
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    data = request.get_json()
    status = data.get("status", "")
    result = analytics_service.update_churn_status(churn_id, status)
    if not result:
        return jsonify({"code": 400, "message": "Invalid churn_id or status"}), 400

    return jsonify({"code": 200, "message": "success", "data": result}), 200


# ============================================================
# Churn Trend
# ============================================================
@analytics_bp.route("/analytics/churn/trend", methods=["GET"])
@jwt_required()
def churn_trend():
    if not _require_admin():
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    data = analytics_service.get_churn_trend()
    return jsonify({"code": 200, "message": "success", "data": data}), 200


# ============================================================
# Sales Heatmap
# ============================================================
@analytics_bp.route("/analytics/sales/heatmap", methods=["GET"])
@jwt_required()
def sales_heatmap():
    if not _require_admin():
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    data = analytics_service.get_sales_heatmap()
    return jsonify({"code": 200, "message": "success", "data": data}), 200


# ============================================================
# Prediction Metrics
# ============================================================
@analytics_bp.route("/analytics/sales/prediction-metrics", methods=["GET"])
@jwt_required()
def prediction_metrics():
    if not _require_admin():
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    data = analytics_service.get_prediction_metrics()
    return jsonify({"code": 200, "message": "success", "data": data}), 200


# ============================================================
# Model Visualization Data (precomputed JSON)
# ============================================================
@analytics_bp.route("/analytics/viz/<model>", methods=["GET"])
@jwt_required()
def model_viz(model):
    if not _require_admin():
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    data = analytics_service.get_model_viz(model)
    if data is None:
        return jsonify({"code": 404, "message": f"No viz data for model '{model}' (may need recompute)"}), 404
    return jsonify({"code": 200, "message": "success", "data": data}), 200
