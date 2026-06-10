from datetime import datetime, timezone
from app.extensions import db


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    image = db.Column(db.String(500), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    stock = db.Column(db.Integer, default=100)
    type = db.Column(db.String(30), nullable=False)
    category_name = db.Column(db.String(20), default="")
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    order_items = db.relationship("OrderItem", backref="product", lazy="dynamic")
    behaviors = db.relationship("UserBehavior", backref="product", lazy="dynamic")

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name or "",
            "description": self.description or "",
            "image": self.image,
            "price": self.price,
            "stock": self.stock,
            "type": self.type or "",
            "category_name": self.category_name or "",
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }