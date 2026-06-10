from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.order import Order, OrderItem, OrderStatusLog, CartItem
from app.models.product import Product
from app.models.user import User
from app.models.analytics import UserBehavior, RFMAnalysis, SalesPrediction, AssociationRule, ChurnPrediction, ModelMetric, Review
from app.extensions import db
import os

admin_bp = Blueprint("admin", __name__)


def _require_admin():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user or user.role != "admin":
        return None, jsonify({"code": 403, "message": "Admin access required"}), 403
    return user, None, None


@admin_bp.route("/admin/orders", methods=["GET"])
@jwt_required()
def get_all_orders():
    user, error_response, status_code = _require_admin()
    if error_response:
        return error_response, status_code

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    status = request.args.get("status")

    query = Order.query
    if status:
        query = query.filter_by(status=status)

    pagination = query.order_by(Order.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        "code": 200,
        "message": "success",
        "data": {
            "orders": [o.to_dict() for o in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "page": page,
        },
    }), 200


@admin_bp.route("/admin/orders/<int:order_id>/ship", methods=["PUT"])
@jwt_required()
def ship_order(order_id):
    _, error_response, status_code = _require_admin()
    if error_response:
        return error_response, status_code

    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"code": 404, "message": "Order not found"}), 404
    if not order.can_transition_to(Order.STATUS_SHIPPED):
        return jsonify({
            "code": 400,
            "message": f"Cannot ship order with status '{order.status}'",
        }), 400

    old_status = order.status
    order.status = Order.STATUS_SHIPPED
    data = request.get_json(silent=True) or {}
    tracking_number = data.get("tracking_number", "")
    if tracking_number:
        order.tracking_number = tracking_number
    OrderStatusLog.create(order.id, old_status, Order.STATUS_SHIPPED)
    db.session.commit()

    return jsonify({"code": 200, "message": "Order shipped", "data": order.to_dict()}), 200


@admin_bp.route("/admin/orders/<int:order_id>/deliver", methods=["PUT"])
@jwt_required()
def deliver_order(order_id):
    _, error_response, status_code = _require_admin()
    if error_response:
        return error_response, status_code

    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"code": 404, "message": "Order not found"}), 404
    if not order.can_transition_to(Order.STATUS_DELIVERED):
        return jsonify({
            "code": 400,
            "message": f"Cannot deliver order with status '{order.status}'",
        }), 400

    old_status = order.status
    order.status = Order.STATUS_DELIVERED
    OrderStatusLog.create(order.id, old_status, Order.STATUS_DELIVERED)
    db.session.commit()

    return jsonify({"code": 200, "message": "Order delivered", "data": order.to_dict()}), 200


@admin_bp.route("/admin/orders/<int:order_id>/refund", methods=["POST"])
@jwt_required()
def refund_order(order_id):
    _, error_response, status_code = _require_admin()
    if error_response:
        return error_response, status_code

    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"code": 404, "message": "Order not found"}), 404
    if not order.can_transition_to(Order.STATUS_REFUNDED):
        return jsonify({
            "code": 400,
            "message": f"Cannot refund order with status '{order.status}'",
        }), 400

    user = db.session.get(User, order.user_id)
    if user:
        user.balance += order.total_amount

    old_status = order.status
    order.status = Order.STATUS_REFUNDED
    OrderStatusLog.create(order.id, old_status, Order.STATUS_REFUNDED)
    db.session.commit()

    return jsonify({"code": 200, "message": "Order refunded", "data": order.to_dict()}), 200


@admin_bp.route("/admin/orders/<int:order_id>/pay", methods=["POST"])
@jwt_required()
def admin_pay_order(order_id):
    _, error_response, status_code = _require_admin()
    if error_response:
        return error_response, status_code

    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({"code": 404, "message": "Order not found"}), 404
    if order.status != Order.STATUS_PENDING:
        return jsonify({
            "code": 400,
            "message": f"Cannot pay order with status '{order.status}'",
        }), 400

    order.status = Order.STATUS_PAID
    OrderStatusLog.create(order.id, order.STATUS_PENDING, Order.STATUS_PAID)
    db.session.commit()

    from app.services.analytics_service import update_user_rfm
    update_user_rfm(order.user_id)

    return jsonify({"code": 200, "message": "Payment successful", "data": order.to_dict()}), 200


@admin_bp.route("/admin/users", methods=["GET"])
@jwt_required()
def get_all_users():
    _, error_response, status_code = _require_admin()
    if error_response:
        return error_response, status_code

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    pagination = User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        "code": 200,
        "message": "success",
        "data": {
            "users": [u.to_dict() for u in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "page": page,
        },
    }), 200


@admin_bp.route("/admin/users/<int:user_id>/balance", methods=["PUT"])
@jwt_required()
def adjust_balance(user_id):
    _, error_response, status_code = _require_admin()
    if error_response:
        return error_response, status_code

    user = db.session.get(User, user_id)
    if not user:
        return jsonify({"code": 404, "message": "User not found"}), 404

    data = request.get_json()
    amount = data.get("amount", 0)
    if not isinstance(amount, (int, float)):
        return jsonify({"code": 400, "message": "Amount must be a number"}), 400
    if abs(amount) > 10000000:
        return jsonify({"code": 400, "message": "Amount exceeds limit"}), 400
    if user.balance + amount < 0:
        return jsonify({"code": 400, "message": "Balance cannot be negative"}), 400
    user.balance += amount
    db.session.commit()

    return jsonify({
        "code": 200,
        "message": f"Balance adjusted by {amount}",
        "data": user.to_dict(),
    }), 200


@admin_bp.route("/admin/reset", methods=["POST"])
@jwt_required()
def admin_reset():
    _, error_response, status_code = _require_admin()
    if error_response:
        return error_response, status_code

    data = request.get_json() or {}
    mode = data.get("mode", "accounts")

    if mode == "all":
        # 清空分析结果
        for model in [UserBehavior, RFMAnalysis, SalesPrediction,
                      AssociationRule, ChurnPrediction, ModelMetric, Review]:
            model.query.delete()

        # 清空购物车（永远是测试数据）
        CartItem.query.delete()

        # 只删测试用户的订单（UCI用户的email以@shopminer.uci结尾）
        uci_emails_like = "%@shopminer.uci"
        uci_users = User.query.filter(User.email.like(uci_emails_like)).all()
        test_user_ids = [u.id for u in User.query.all()
                         if not u.email.endswith("@shopminer.uci")
                         and u.email not in ("admin@shopminer.com", "customer@shopminer.com")]
        if test_user_ids:
            test_order_ids = [o.id for o in Order.query.filter(Order.user_id.in_(test_user_ids)).all()]
            if test_order_ids:
                OrderItem.query.filter(OrderItem.order_id.in_(test_order_ids)).delete()
                OrderStatusLog.query.filter(OrderStatusLog.order_id.in_(test_order_ids)).delete()
                Order.query.filter(Order.id.in_(test_order_ids)).delete()
            # 清理测试用户（可选）
            # User.query.filter(User.id.in_(test_user_ids)).delete()
        db.session.commit()

    admin_user = User.query.filter_by(email="admin@shopminer.com").first()
    if admin_user:
        admin_user.first_name = "Admin"
        admin_user.last_name = "User"
        admin_user.address = "Admin Address"
        admin_user.phone = ""
        admin_user.balance = 1000000
        admin_user.role = "admin"
        admin_user.set_password("Admin@123")

    customer_user = User.query.filter_by(email="customer@shopminer.com").first()
    if customer_user:
        customer_user.first_name = "Customer"
        customer_user.last_name = "Test"
        customer_user.address = "123 Test St"
        customer_user.phone = ""
        customer_user.balance = 500000
        customer_user.role = "customer"
        customer_user.set_password("Customer@123")

    db.session.commit()

    msg = "系统账户已重置为默认信息"
    if mode == "all":
        msg = "已清空所有测试数据（订单、购物车、评价、分析结果），商品和用户数据不受影响"

    return jsonify({"code": 200, "message": msg}), 200


@admin_bp.route("/admin/products", methods=["GET"])
@jwt_required()
def get_admin_products():
    _, error_response, status_code = _require_admin()
    if error_response:
        return error_response, status_code

    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    search = request.args.get("q", "").strip()
    is_active = request.args.get("is_active")

    query = Product.query

    if search:
        query = query.filter(
            db.or_(
                Product.name.contains(search),
                Product.description.contains(search),
            )
        )
    if is_active is not None:
        if is_active.lower() in ("1", "true", "yes"):
            query = query.filter_by(is_active=True)
        elif is_active.lower() in ("0", "false", "no"):
            query = query.filter_by(is_active=False)

    pagination = query.order_by(Product.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return jsonify({
        "code": 200,
        "message": "success",
        "data": {
            "products": [p.to_dict() for p in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "page": page,
        },
    }), 200


@admin_bp.route("/admin/products/<int:product_id>", methods=["GET"])
@jwt_required()
def get_admin_product(product_id):
    _, error_response, status_code = _require_admin()
    if error_response:
        return error_response, status_code

    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"code": 404, "message": "Product not found"}), 404

    return jsonify({"code": 200, "message": "success", "data": product.to_dict()}), 200


@admin_bp.route("/admin/products", methods=["POST"])
@jwt_required()
def create_product():
    _, error_response, status_code = _require_admin()
    if error_response:
        return error_response, status_code

    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"code": 400, "message": "Product name is required"}), 400

    price = data.get("price", 0)
    if not isinstance(price, int) or price <= 0:
        return jsonify({"code": 400, "message": "Price must be a positive integer (fen)"}), 400

    stock = data.get("stock", 0)
    if not isinstance(stock, int) or stock < 0:
        return jsonify({"code": 400, "message": "Stock must be a non-negative integer"}), 400

    product = Product(
        name=name,
        description=(data.get("description") or "").strip(),
        image=(data.get("image") or "").strip(),
        price=price,
        stock=stock,
        type=(data.get("type") or "physical").strip(),
        category_name=(data.get("category_name") or "").strip(),
        is_active=True,
    )
    db.session.add(product)
    db.session.commit()

    return jsonify({"code": 200, "message": "Product created", "data": product.to_dict()}), 200


@admin_bp.route("/admin/products/<int:product_id>", methods=["PUT"])
@jwt_required()
def update_product(product_id):
    _, error_response, status_code = _require_admin()
    if error_response:
        return error_response, status_code

    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"code": 404, "message": "Product not found"}), 404

    data = request.get_json(silent=True) or {}

    if "name" in data:
        name = (data["name"] or "").strip()
        if not name:
            return jsonify({"code": 400, "message": "Product name cannot be empty"}), 400
        product.name = name
    if "description" in data:
        product.description = (data["description"] or "").strip()
    if "image" in data:
        product.image = (data["image"] or "").strip()
    if "price" in data:
        price = data["price"]
        if not isinstance(price, int) or price <= 0:
            return jsonify({"code": 400, "message": "Price must be a positive integer (fen)"}), 400
        product.price = price
    if "stock" in data:
        stock = data["stock"]
        if not isinstance(stock, int) or stock < 0:
            return jsonify({"code": 400, "message": "Stock must be a non-negative integer"}), 400
        product.stock = stock
    if "type" in data:
        product.type = (data["type"] or "physical").strip()
    if "category_name" in data:
        product.category_name = (data["category_name"] or "").strip()

    db.session.commit()

    return jsonify({"code": 200, "message": "Product updated", "data": product.to_dict()}), 200


@admin_bp.route("/admin/products/<int:product_id>/toggle-active", methods=["PUT"])
@jwt_required()
def toggle_product_active(product_id):
    _, error_response, status_code = _require_admin()
    if error_response:
        return error_response, status_code

    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"code": 404, "message": "Product not found"}), 404

    product.is_active = not product.is_active
    db.session.commit()

    action = "activated" if product.is_active else "deactivated"
    return jsonify({
        "code": 200,
        "message": f"Product {action}",
        "data": product.to_dict(),
    }), 200


@admin_bp.route("/admin/import-data", methods=["POST"])
@jwt_required()
def admin_import_data():
    _, error_response, status_code = _require_admin()
    if error_response:
        return error_response, status_code

    import subprocess, sys as _sys
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    script_path = os.path.join(project_root, "scripts", "import_uci_data.py")

    if not os.path.exists(script_path):
        return jsonify({"code": 404, "message": "import_uci_data.py not found"}), 404

    try:
        proc = subprocess.Popen(
            [_sys.executable, script_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=project_root,
        )
        return jsonify({"code": 200, "message": "数据导入已启动（后台运行中）"}), 200
    except Exception as e:
        return jsonify({"code": 500, "message": f"启动导入失败: {str(e)}"}), 500