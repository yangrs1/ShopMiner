from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.product import Product
from app.models.analytics import UserBehavior, Review
from app.extensions import db

product_bp = Blueprint("product", __name__)


@product_bp.route("/products", methods=["GET"])
def get_products():
    page = request.args.get("page", 1, type=int)
    per_page = request.args.get("per_page", 20, type=int)
    product_type = request.args.get("type")
    category = request.args.get("category")
    search = request.args.get("q", "").strip()
    min_price = request.args.get("min_price", type=int)
    max_price = request.args.get("max_price", type=int)
    sort_by = request.args.get("sort_by", "created_at")
    order = request.args.get("order", "desc")

    # Validate sort_by
    valid_sort = ["price", "rating", "created_at"]
    if sort_by not in valid_sort:
        return jsonify({"code": 400, "message": f"Invalid sort_by. Must be one of: {', '.join(valid_sort)}"}), 400

    # Validate order
    if order not in ("asc", "desc"):
        return jsonify({"code": 400, "message": "Invalid order. Must be 'asc' or 'desc'"}), 400

    # Validate price range
    if (min_price is not None and min_price < 0) or (max_price is not None and max_price < 0):
        return jsonify({"code": 400, "message": "Price cannot be negative"}), 400
    if min_price is not None and max_price is not None and min_price > max_price:
        return jsonify({"code": 400, "message": "min_price cannot be greater than max_price"}), 400

    query = Product.query.filter_by(is_active=True)

    if product_type:
        query = query.filter_by(type=product_type)
    if category:
        query = query.filter_by(category_name=category)
    if search:
        query = query.filter(
            db.or_(
                Product.name.contains(search),
                Product.description.contains(search),
            )
        )
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)

    # Apply sorting
    order_func = db.asc if order == "asc" else db.desc
    if sort_by == "price":
        query = query.order_by(order_func(Product.price), Product.id)
    elif sort_by == "rating":
        avg_rating_subq = db.session.query(
            Review.product_id,
            db.func.avg(Review.rating).label("avg_rating")
        ).group_by(Review.product_id).subquery()

        query = query.outerjoin(
            avg_rating_subq,
            Product.id == avg_rating_subq.c.product_id
        )

        if order == "desc":
            query = query.order_by(avg_rating_subq.c.avg_rating.desc().nullslast(), Product.id)
        else:
            query = query.order_by(avg_rating_subq.c.avg_rating.asc().nullslast(), Product.id)
    else:  # created_at (default)
        query = query.order_by(order_func(Product.created_at), Product.id)

    pagination = query.paginate(
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


@product_bp.route("/products/categories", methods=["GET"])
def get_categories():
    categories = db.session.query(
        Product.category_name,
        db.func.count(Product.id).label("count"),
    ).filter(
        Product.is_active == True,
        Product.category_name != "",
    ).group_by(Product.category_name).order_by(Product.category_name).all()

    return jsonify({
        "code": 200,
        "message": "success",
        "data": {
            "categories": [
                {"name": c[0], "count": c[1]} for c in categories
            ],
        },
    }), 200


@product_bp.route("/products/ratings", methods=["GET"])
def get_products_ratings():
    product_ids = request.args.get("product_ids", "")
    ids = [int(x.strip()) for x in product_ids.split(",") if x.strip().isdigit()]

    if not ids:
        return jsonify({"code": 200, "message": "success", "data": {}}), 200

    results = db.session.query(
        Review.product_id,
        db.func.avg(Review.rating).label("avg_rating"),
        db.func.count(Review.id).label("total_reviews"),
    ).filter(Review.product_id.in_(ids)).group_by(Review.product_id).all()

    ratings = {}
    for r in results:
        ratings[r.product_id] = {
            "avg_rating": round(float(r.avg_rating), 1) if r.avg_rating else 0,
            "total_reviews": r.total_reviews or 0,
        }

    return jsonify({
        "code": 200,
        "message": "success",
        "data": ratings,
    }), 200


@product_bp.route("/products/<int:product_id>", methods=["GET"])
@jwt_required(optional=True)
def get_product(product_id):
    product = db.session.get(Product, product_id)
    if not product or not product.is_active:
        return jsonify({"code": 404, "message": "Product not found"}), 404

    try:
        user_id = get_jwt_identity()
        if user_id:
            behavior = UserBehavior(user_id=int(user_id), product_id=product_id, action="view")
            db.session.add(behavior)
            db.session.commit()
    except Exception:
        pass

    return jsonify({"code": 200, "message": "success", "data": product.to_dict()}), 200


@product_bp.route("/products", methods=["POST"])
@jwt_required()
def create_product():
    user_id = int(get_jwt_identity())
    from app.models.user import User
    user = db.session.get(User, user_id)
    if not user or user.role != "admin":
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"code": 400, "message": "Request body is required"}), 400

    required_fields = ["name", "description", "image", "price", "type", "stock"]
    for field in required_fields:
        if field not in data:
            return jsonify({"code": 400, "message": f"Missing field: {field}"}), 400

    if not isinstance(data["price"], (int, float)) or data["price"] < 0:
        return jsonify({"code": 400, "message": "Price must be a non-negative number"}), 400
    if not isinstance(data.get("stock", 100), int) or data.get("stock", 100) < 0:
        return jsonify({"code": 400, "message": "Stock must be a non-negative integer"}), 400

    product = Product(
        name=data["name"],
        description=data["description"],
        image=data["image"],
        price=data["price"],
        stock=data.get("stock", 100),
        type=data["type"],
        category_name=data.get("category_name", ""),
    )
    db.session.add(product)
    db.session.commit()

    return jsonify({
        "code": 201,
        "message": "Product created",
        "data": product.to_dict(),
    }), 201


@product_bp.route("/products/<int:product_id>", methods=["PUT"])
@jwt_required()
def update_product(product_id):
    user_id = int(get_jwt_identity())
    from app.models.user import User
    user = db.session.get(User, user_id)
    if not user or user.role != "admin":
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"code": 404, "message": "Product not found"}), 404

    data = request.get_json()
    if "price" in data and (not isinstance(data["price"], (int, float)) or data["price"] < 0):
        return jsonify({"code": 400, "message": "Price must be a non-negative number"}), 400
    if "stock" in data and (not isinstance(data["stock"], int) or data["stock"] < 0):
        return jsonify({"code": 400, "message": "Stock must be a non-negative integer"}), 400
    for field in ["name", "description", "image", "price", "stock", "type", "category_name", "is_active"]:
        if field in data:
            setattr(product, field, data[field])

    db.session.commit()
    return jsonify({"code": 200, "message": "Product updated", "data": product.to_dict()}), 200


@product_bp.route("/products/<int:product_id>", methods=["DELETE"])
@jwt_required()
def deactivate_product(product_id):
    user_id = int(get_jwt_identity())
    from app.models.user import User
    user = db.session.get(User, user_id)
    if not user or user.role != "admin":
        return jsonify({"code": 403, "message": "Admin access required"}), 403

    product = db.session.get(Product, product_id)
    if not product:
        return jsonify({"code": 404, "message": "Product not found"}), 404

    product.is_active = False
    db.session.commit()
    return jsonify({"code": 200, "message": "Product deactivated"}), 200


@product_bp.route("/products/<int:product_id>/rating", methods=["GET"])
def get_product_rating(product_id):
    result = db.session.query(
        db.func.avg(Review.rating).label("avg_rating"),
        db.func.count(Review.id).label("total_reviews"),
    ).filter(Review.product_id == product_id).first()

    avg_rating = round(float(result.avg_rating), 1) if result and result.avg_rating else 0
    total_reviews = result.total_reviews if result and result.total_reviews else 0

    return jsonify({
        "code": 200,
        "message": "success",
        "data": {
            "product_id": product_id,
            "avg_rating": avg_rating,
            "total_reviews": total_reviews,
        },
    }), 200