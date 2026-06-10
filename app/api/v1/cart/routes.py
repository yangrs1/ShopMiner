from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.order import CartItem
from app.models.product import Product
from app.models.analytics import UserBehavior

cart_bp = Blueprint("cart", __name__)


@cart_bp.route("/cart", methods=["GET"])
@jwt_required()
def get_cart():
    user_id = int(get_jwt_identity())
    items = CartItem.query.filter_by(user_id=user_id).all()
    cart = [item.to_dict() for item in items]
    total = sum(i["price"] * i["quantity"] for i in cart)
    return jsonify({
        "code": 200,
        "message": "success",
        "data": {
            "items": cart,
            "total_amount": total,
            "item_count": len(cart),
        },
    }), 200


@cart_bp.route("/cart", methods=["POST"])
@jwt_required()
def add_to_cart():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

    if not product_id:
        return jsonify({"code": 400, "message": "product_id is required"}), 400

    if not isinstance(quantity, int) or quantity <= 0:
        return jsonify({"code": 400, "message": "Quantity must be a positive integer"}), 400

    product = db.session.get(Product, product_id)
    if not product or not product.is_active:
        return jsonify({"code": 404, "message": "Product not found"}), 404

    existing = CartItem.query.filter_by(user_id=user_id, product_id=product_id).first()
    if existing:
        new_qty = existing.quantity + quantity
        if new_qty > product.stock:
            return jsonify({"code": 400, "message": "Insufficient stock"}), 400
        existing.quantity = new_qty
    else:
        if quantity > product.stock:
            return jsonify({"code": 400, "message": "Insufficient stock"}), 400
        db.session.add(CartItem(user_id=user_id, product_id=product_id, quantity=quantity))

    db.session.add(UserBehavior(user_id=user_id, product_id=product_id, action="add_to_cart"))
    db.session.commit()

    items = CartItem.query.filter_by(user_id=user_id).all()
    return jsonify({
        "code": 200,
        "message": "Product added to cart",
        "data": [item.to_dict() for item in items],
    }), 200


@cart_bp.route("/cart/<int:product_id>", methods=["PUT"])
@jwt_required()
def update_cart_item(product_id):
    user_id = int(get_jwt_identity())
    data = request.get_json()
    if "quantity" not in data:
        return jsonify({"code": 400, "message": "Quantity is required"}), 400
    quantity = data.get("quantity")
    if not isinstance(quantity, int) or quantity < 1:
        return jsonify({"code": 400, "message": "Quantity must be a positive integer"}), 400

    item = CartItem.query.filter_by(user_id=user_id, product_id=product_id).first()
    if not item:
        return jsonify({"code": 404, "message": "Item not in cart"}), 404

    product = db.session.get(Product, product_id)
    if quantity > product.stock:
        return jsonify({"code": 400, "message": "Insufficient stock"}), 400

    item.quantity = quantity
    db.session.commit()

    items = CartItem.query.filter_by(user_id=user_id).all()
    return jsonify({"code": 200, "message": "Quantity updated", "data": [i.to_dict() for i in items]}), 200


@cart_bp.route("/cart/<int:product_id>", methods=["DELETE"])
@jwt_required()
def remove_from_cart(product_id):
    user_id = int(get_jwt_identity())
    item = CartItem.query.filter_by(user_id=user_id, product_id=product_id).first()
    if not item:
        return jsonify({"code": 404, "message": "Cart item not found"}), 404
    db.session.delete(item)
    db.session.commit()
    items = CartItem.query.filter_by(user_id=user_id).all()
    return jsonify({"code": 200, "message": "Item removed from cart", "data": [i.to_dict() for i in items]}), 200


@cart_bp.route("/cart", methods=["DELETE"])
@jwt_required()
def clear_cart():
    user_id = int(get_jwt_identity())
    CartItem.query.filter_by(user_id=user_id).delete()
    db.session.commit()
    return jsonify({"code": 200, "message": "Cart cleared", "data": []}), 200
