from datetime import datetime, timezone
from app.extensions import db, bcrypt


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(60), nullable=False)
    last_name = db.Column(db.String(60), nullable=False)
    phone = db.Column(db.String(20), default="")
    address = db.Column(db.String(250), default="")
    email = db.Column(db.String(250), unique=True, nullable=False, index=True)
    password = db.Column(db.String(250), nullable=False)
    icon = db.Column(db.String(250), default="icon_bear.png")
    balance = db.Column(db.Integer, default=0)
    role = db.Column(db.String(20), default="customer")
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    orders = db.relationship("Order", backref="user", lazy="dynamic")
    behaviors = db.relationship("UserBehavior", backref="user", lazy="dynamic")

    def set_password(self, password):
        self.password = bcrypt.generate_password_hash(password).decode("utf-8")

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password, password)

    def to_dict(self):
        return {
            "id": self.id,
            "first_name": self.first_name or "",
            "last_name": self.last_name or "",
            "phone": self.phone or "",
            "address": self.address or "",
            "email": self.email,
            "icon": self.icon,
            "balance": self.balance,
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }