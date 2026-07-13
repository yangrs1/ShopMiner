from datetime import datetime, timezone
from app.extensions import db
from sqlalchemy import UniqueConstraint


class UserBehavior(db.Model):
    __tablename__ = "user_behaviors"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    action = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # [GAP: missing-test] UserBehavior.to_dict() has no unit test
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "action": self.action,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class RFMAnalysis(db.Model):
    __tablename__ = "rfm_analysis"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    recency = db.Column(db.Integer, nullable=False)
    frequency = db.Column(db.Integer, nullable=False)
    monetary = db.Column(db.Integer, nullable=False)
    r_score = db.Column(db.Integer, nullable=False)
    f_score = db.Column(db.Integer, nullable=False)
    m_score = db.Column(db.Integer, nullable=False)
    rfm_score = db.Column(db.Integer, nullable=False)
    segment = db.Column(db.String(50), nullable=False)
    analyzed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # [GAP: missing-test] RFMAnalysis.to_dict() has no unit test
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "recency": self.recency,
            "frequency": self.frequency,
            "monetary": self.monetary,
            "r_score": self.r_score,
            "f_score": self.f_score,
            "m_score": self.m_score,
            "rfm_score": self.rfm_score,
            "segment": self.segment,
            "analyzed_at": self.analyzed_at.isoformat() if self.analyzed_at else None,
        }


class SalesPrediction(db.Model):
    __tablename__ = "sales_predictions"

    id = db.Column(db.Integer, primary_key=True)
    pred_date = db.Column(db.Date, nullable=False, index=True)
    pred_amount = db.Column(db.Float, nullable=False)
    pred_upper = db.Column(db.Float, nullable=True)
    pred_lower = db.Column(db.Float, nullable=True)
    model_name = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # [GAP: missing-test] SalesPrediction.to_dict() has no unit test
    def to_dict(self):
        return {
            "id": self.id,
            "pred_date": self.pred_date.isoformat() if self.pred_date else None,
            "pred_amount": self.pred_amount,
            "pred_upper": self.pred_upper,
            "pred_lower": self.pred_lower,
            "model_name": self.model_name,
        }


class AssociationRule(db.Model):
    __tablename__ = "association_rules"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True, index=True)
    antecedent = db.Column(db.String(200), nullable=False)
    consequent = db.Column(db.String(200), nullable=False)
    consequent_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=True)
    support = db.Column(db.Float, nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    lift = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # [GAP: missing-test] AssociationRule.to_dict() has no unit test
    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "antecedent": self.antecedent,
            "consequent": self.consequent,
            "consequent_id": self.consequent_id,
            "support": round(self.support, 4),
            "confidence": round(self.confidence, 4),
            "lift": round(self.lift, 4),
        }


class ChurnPrediction(db.Model):
    __tablename__ = "churn_predictions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    churn_prob = db.Column(db.Float, nullable=False)
    is_churn_risk = db.Column(db.Boolean, default=False)
    top_features = db.Column(db.String(500), default="[]")
    model_name = db.Column(db.String(30), default="XGBoost+SMOTE+Optuna")
    status = db.Column(db.String(20), default="pending")  # pending / contacted / resolved
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # [GAP: missing-test] ChurnPrediction.to_dict() has no unit test
    def to_dict(self):
        import json
        top_features_raw = self.top_features or "[]"
        try:
            top_features_list = json.loads(top_features_raw)
        except (json.JSONDecodeError, TypeError):
            top_features_list = [top_features_raw] if top_features_raw and top_features_raw != "[]" else []
        return {
            "id": self.id,
            "user_id": self.user_id,
            "churn_prob": round(self.churn_prob, 4),
            "is_churn_risk": self.is_churn_risk,
            "top_features": top_features_list,
            "model_name": self.model_name,
            "status": self.status,
        }


class ModelMetric(db.Model):
    __tablename__ = "model_metrics"

    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(50), nullable=False, index=True)
    metric_name = db.Column(db.String(50), nullable=False)
    metric_value = db.Column(db.Float, nullable=False)
    detail = db.Column(db.String(500), default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # [GAP: missing-test] ModelMetric.to_dict() has no unit test
    def to_dict(self):
        return {
            "id": self.id,
            "model_name": self.model_name,
            "metric_name": self.metric_name,
            "metric_value": round(self.metric_value, 6),
            "detail": self.detail,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Review(db.Model):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=True)
    rating = db.Column(db.Integer, nullable=False)
    content = db.Column(db.String(500), default="")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", lazy="joined")
    product = db.relationship("Product", lazy="joined")

    # [GAP: missing-test] Review.to_dict() has no unit test
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "user_name": f"{self.user.first_name} {self.user.last_name}" if self.user else "",
            "product_id": self.product_id,
            "product_name": self.product.name if self.product else "",
            "order_id": self.order_id,
            "rating": self.rating,
            "content": self.content or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Favorite(db.Model):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "product_id", name="uq_favorite_user_product"),)

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    product = db.relationship("Product", lazy="joined")

    # [GAP: missing-test] Favorite.to_dict() has no unit test
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "product_id": self.product_id,
            "product": self.product.to_dict() if self.product else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }