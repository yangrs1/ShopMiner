from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services import order_service

order_bp = Blueprint("order", __name__)


@order_bp.route("/orders", methods=["POST"])
@jwt_required()
def create_order():
    user_id = int(get_jwt_identity())
    data = request.get_json(silent=True) or {}
    shipping_address = data.get("shipping_address", "")
    shipping_phone = data.get("shipping_phone", "")
    order, error = order_service.create_order_from_cart(user_id, shipping_address, shipping_phone)
    if error:
        code = 400
        if "Access denied" in error:
            code = 403
        return jsonify({"code": code, "message": error}), code

    return jsonify({
        "code": 201,
        "message": "Order created successfully",
        "data": order.to_dict(),
    }), 201


@order_bp.route("/orders", methods=["GET"])
@jwt_required()
def get_orders():
    user_id = int(get_jwt_identity())
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    pagination = order_service.get_user_orders(user_id, page, per_page)
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


@order_bp.route("/orders/<int:order_id>", methods=["GET"])
@jwt_required()
def get_order(order_id):
    user_id = int(get_jwt_identity())
    order, error = order_service.get_order_with_access_check(order_id, user_id)
    if error:
        code = 404 if "not found" in error else 403
        return jsonify({"code": code, "message": error}), code

    return jsonify({"code": 200, "message": "success", "data": order.to_dict()}), 200


@order_bp.route("/orders/<int:order_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_order(order_id):
    user_id = int(get_jwt_identity())
    order, error = order_service.cancel_order(user_id, order_id)
    if error:
        code = 404 if "not found" in error else 400
        if "Access denied" in error:
            code = 403
        return jsonify({"code": code, "message": error}), code

    return jsonify({
        "code": 200,
        "message": "Order cancelled and refunded",
        "data": order.to_dict(),
    }), 200


@order_bp.route("/orders/<int:order_id>/pay", methods=["POST"])
@jwt_required()
def pay_order(order_id):
    user_id = int(get_jwt_identity())
    order, error = order_service.pay_order(user_id, order_id)
    if error:
        code = 404 if "not found" in error else 403 if "Access denied" in error else 400
        return jsonify({"code": code, "message": error}), code

    return jsonify({
        "code": 200,
        "message": "Payment successful",
        "data": order.to_dict(),
    }), 200


@order_bp.route("/orders/<int:order_id>/deliver", methods=["POST"])
@jwt_required()
def confirm_delivery(order_id):
    user_id = int(get_jwt_identity())
    order, error = order_service.confirm_delivery(user_id, order_id)
    if error:
        code = 404 if "not found" in error else 400
        return jsonify({"code": code, "message": error}), code
    return jsonify({
        "code": 200,
        "message": "Delivery confirmed",
        "data": order.to_dict(),
    }), 200


@order_bp.route("/orders/<int:order_id>/status-logs", methods=["GET"])
@jwt_required()
def get_order_status_logs(order_id):
    user_id = int(get_jwt_identity())
    order, error = order_service.get_order_with_access_check(order_id, user_id)
    if error:
        code = 404 if "not found" in error else 403
        return jsonify({"code": code, "message": error}), code

    from app.models.order import OrderStatusLog
    logs = OrderStatusLog.query.filter_by(order_id=order_id).order_by(
        OrderStatusLog.created_at.asc()
    ).all()
    return jsonify({
        "code": 200,
        "message": "success",
        "data": [log.to_dict() for log in logs],
    }), 200
