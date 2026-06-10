from app.models.order import Order, OrderItem, OrderStatusLog, CartItem
from app.models.product import Product
from app.models.user import User
from app.models.analytics import UserBehavior
from app.extensions import db
from app.services.analytics_service import update_user_rfm


def get_cart_items(user_id):
    return CartItem.query.filter_by(user_id=user_id).all()


def create_order_from_cart(user_id, shipping_address="", shipping_phone=""):
    user = db.session.get(User, user_id)
    cart_items = get_cart_items(user_id)

    if not cart_items:
        return None, "Cart is empty"

    total_amount = 0
    for ci in cart_items:
        product = ci.product
        if not product or not product.is_active:
            return None, f"Product '{product.name if product else ci.product_id}' is no longer available"
        total_amount += product.price * ci.quantity

    addr = shipping_address or user.address or ""
    phone = shipping_phone or user.phone or ""

    order = Order(
        user_id=user_id,
        total_amount=total_amount,
        shipping_address=addr,
        shipping_phone=phone,
        status=Order.STATUS_PENDING
    )
    db.session.add(order)
    db.session.flush()

    OrderStatusLog.create(order.id, None, Order.STATUS_PENDING)

    # Stock check & deduction inside transaction to prevent overselling
    for ci in cart_items:
        product = ci.product
        # In production with PostgreSQL, use Product.query.with_for_update().get(id) for row-level locking
        db.session.refresh(product)
        if product.stock < ci.quantity:
            db.session.rollback()
            return None, f"Insufficient stock for '{product.name}'"
        product.stock -= ci.quantity
        db.session.add(OrderItem(
            order_id=order.id,
            product_id=ci.product_id,
            quantity=ci.quantity,
            unit_price=product.price,
        ))
        db.session.add(UserBehavior(
            user_id=user_id,
            product_id=ci.product_id,
            action="purchase",
        ))

    # Balance check inside transaction to prevent race conditions
    db.session.refresh(user)
    if user.balance < total_amount:
        db.session.rollback()
        return None, f"Insufficient balance. Need {total_amount}, have {user.balance}"

    # Clear cart
    CartItem.query.filter_by(user_id=user_id).delete()
    db.session.commit()

    return order, None


def pay_order(user_id, order_id):
    """用户余额支付订单 (pending → paid)"""
    order = db.session.get(Order, order_id)
    if not order:
        return None, "Order not found"
    if order.user_id != user_id:
        return None, "Access denied"

    if order.status != Order.STATUS_PENDING:
        return None, f"Cannot pay order with status '{order.status}'"

    user = db.session.get(User, user_id)
    if user.balance < order.total_amount:
        return None, f"Insufficient balance. Need {order.total_amount}, have {user.balance}"

    user.balance -= order.total_amount
    old_status = order.status
    order.status = Order.STATUS_PAID
    OrderStatusLog.create(order.id, old_status, Order.STATUS_PAID)
    db.session.commit()

    update_user_rfm(user_id)

    return order, None


def cancel_order(user_id, order_id):
    order = db.session.get(Order, order_id)
    if not order:
        return None, "Order not found"
    if order.user_id != user_id:
        return None, "Access denied"
    if not order.can_transition_to(Order.STATUS_CANCELLED):
        return None, f"Cannot cancel order with status '{order.status}'"

    if order.status == Order.STATUS_PAID:
        user = db.session.get(User, user_id)
        user.balance += order.total_amount

    for item in order.items:
        product = db.session.get(Product, item.product_id)
        if product:
            product.stock += item.quantity

    old_status = order.status
    order.status = Order.STATUS_CANCELLED
    OrderStatusLog.create(order.id, old_status, Order.STATUS_CANCELLED)
    db.session.commit()
    return order, None


def get_user_orders(user_id, page=1, per_page=20):
    return Order.query.filter_by(user_id=user_id).order_by(
        Order.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)


def confirm_delivery(user_id, order_id):
    """用户确认收货 (shipped → delivered)"""
    order = db.session.get(Order, order_id)
    if not order:
        return None, "Order not found"
    if order.user_id != user_id:
        return None, "Access denied"
    if not order.can_transition_to(Order.STATUS_DELIVERED):
        return None, f"Cannot confirm delivery for order with status '{order.status}'"

    old_status = order.status
    order.status = Order.STATUS_DELIVERED
    OrderStatusLog.create(order.id, old_status, Order.STATUS_DELIVERED)
    db.session.commit()
    return order, None


def get_order_with_access_check(order_id, user_id):
    order = db.session.get(Order, order_id)
    if not order:
        return None, "Order not found"
    user = db.session.get(User, user_id)
    if order.user_id != user_id and user.role != "admin":
        return None, "Access denied"
    return order, None
