from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.analytics import Favorite
from app.models.product import Product


favorites_bp = Blueprint("favorites", __name__)


@favorites_bp.route("/favorites", methods=["GET"])
@jwt_required()
def list_favorites():
    user_id = int(get_jwt_identity())
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)

    pagination = Favorite.query.filter_by(user_id=user_id).order_by(
        Favorite.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

    return jsonify({
        "code": 200, "message": "success",
        "data": {
            "favorites": [f.to_dict() for f in pagination.items],
            "total": pagination.total,
            "pages": pagination.pages,
            "page": page,
        },
    }), 200


@favorites_bp.route("/favorites", methods=["POST"])
@jwt_required()
def add_favorite():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    product_id = data.get("product_id")

    if not product_id:
        return jsonify({"code": 400, "message": "product_id is required"}), 400

    product = db.session.get(Product, product_id)
    if not product or not product.is_active:
        return jsonify({"code": 404, "message": "Product not found"}), 404

    existing = Favorite.query.filter_by(user_id=user_id, product_id=product_id).first()
    if existing:
        return jsonify({
            "code": 200, "message": "Already favorited",
            "data": existing.to_dict(),
        }), 200

    favorite = Favorite(user_id=user_id, product_id=product_id)
    db.session.add(favorite)
    db.session.commit()

    return jsonify({
        "code": 201, "message": "Added to favorites",
        "data": favorite.to_dict(),
    }), 201


@favorites_bp.route("/favorites/<int:product_id>", methods=["DELETE"])
@jwt_required()
def remove_favorite(product_id):
    user_id = int(get_jwt_identity())
    favorite = Favorite.query.filter_by(user_id=user_id, product_id=product_id).first()
    if favorite:
        db.session.delete(favorite)
        db.session.commit()
    return jsonify({"code": 200, "message": "Removed from favorites"}), 200


@favorites_bp.route("/favorites/check/<int:product_id>", methods=["GET"])
@jwt_required()
def check_favorite(product_id):
    user_id = int(get_jwt_identity())
    favorite = Favorite.query.filter_by(user_id=user_id, product_id=product_id).first()
    return jsonify({
        "code": 200, "message": "success",
        "data": {"favorited": favorite is not None},
    }), 200
