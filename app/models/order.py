from datetime import datetime, timezone
from app.extensions import db


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    total_amount = db.Column(db.Integer, nullable=False)
    freight = db.Column(db.Integer, default=0)
    shipping_address = db.Column(db.String(250), default="")
    shipping_phone = db.Column(db.String(20), default="")
    tracking_number = db.Column(db.String(50), default="")
    status = db.Column(db.String(20), default="pending", index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    items = db.relationship("OrderItem", backref="order", lazy="dynamic", cascade="all, delete-orphan")
    status_logs = db.relationship("OrderStatusLog", backref="order", lazy="dynamic", cascade="all, delete-orphan")

    STATUS_PENDING = "pending"
    STATUS_PAID = "paid"
    STATUS_SHIPPED = "shipped"
    STATUS_DELIVERED = "delivered"
    STATUS_CANCELLED = "cancelled"
    STATUS_REFUNDED = "refunded"

    VALID_TRANSITIONS = {
        STATUS_PENDING: [STATUS_PAID, STATUS_CANCELLED],
        STATUS_PAID: [STATUS_SHIPPED, STATUS_REFUNDED, STATUS_CANCELLED],
        STATUS_SHIPPED: [STATUS_DELIVERED],
    }

    def can_transition_to(self, new_status):
        return new_status in self.VALID_TRANSITIONS.get(self.status, [])

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "total_amount": self.total_amount,
            "freight": self.freight,
            "shipping_address": self.shipping_address or "",
            "shipping_phone": self.shipping_phone or "",
            "tracking_number": self.tracking_number or "",
            "status": self.status,
            "items": [item.to_dict() for item in self.items.all()],
            "status_logs": [log.to_dict() for log in self.status_logs.all()],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        from app.models.product import Product
        product = db.session.get(Product, self.product_id)
        return {
            "id": self.id,
            "order_id": self.order_id,
            "product_id": self.product_id,
            "product_name": product.name if product else "",
            "product_image": product.image if product else "",
            "quantity": self.quantity,
            "unit_price": self.unit_price,
        }


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (db.UniqueConstraint("user_id", "product_id", name="uq_cart_user_product"),)

    product = db.relationship("Product", lazy="joined")

    def to_dict(self):
        p = self.product
        return {
            "id": p.id,
            "product_id": p.id,
            "name": p.name or "",
            "price": p.price,
            "image": p.image,
            "stock": p.stock,
            "quantity": self.quantity,
        }


class OrderStatusLog(db.Model):
    __tablename__ = "order_status_logs"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    from_status = db.Column(db.String(20), nullable=True)
    to_status = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @classmethod
    def create(cls, order_id, from_status, to_status):
        log = cls(order_id=order_id, from_status=from_status, to_status=to_status)
        db.session.add(log)
        return log

    def to_dict(self):
        return {
            "id": self.id,
            "order_id": self.order_id,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }