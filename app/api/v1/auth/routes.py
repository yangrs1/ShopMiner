from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.services import auth_service
from app.extensions import db, limiter
import re

EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"code": 400, "message": "Request body is required"}), 400

    email = data.get("email")
    password = data.get("password")
    first_name = data.get("first_name")
    last_name = data.get("last_name")
    address = data.get("address", "")

    if not all([email, password, first_name, last_name]):
        return jsonify({"code": 400, "message": "Missing required fields"}), 400

    if not EMAIL_REGEX.match(email):
        return jsonify({"code": 400, "message": "Invalid email format"}), 400

    user, error = auth_service.register_user(
        email=email, password=password, first_name=first_name,
        last_name=last_name, address=address,
        icon=data.get("icon", "icon_bear.png"),
    )
    if error:
        if "Password" in error:
            return jsonify({"code": 400, "message": error}), 400
        return jsonify({"code": 409, "message": error}), 409

    access_token = auth_service.generate_token(user)
    return jsonify({
        "code": 201,
        "message": "User registered successfully",
        "data": {"access_token": access_token, "user": user.to_dict()},
    }), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10/minute")
def login():
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"code": 400, "message": "Request body is required"}), 400

    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"code": 400, "message": "Email and password are required"}), 400

    user = auth_service.authenticate_user(email, password)
    if not user:
        return jsonify({"code": 401, "message": "Invalid credentials"}), 401

    access_token = auth_service.generate_token(user)
    return jsonify({
        "code": 200,
        "message": "Login successful",
        "data": {"access_token": access_token, "user": user.to_dict()},
    }), 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user_id = int(get_jwt_identity())
    user = auth_service.get_user_by_id(user_id)
    if not user:
        return jsonify({"code": 404, "message": "User not found"}), 404
    return jsonify({"code": 200, "message": "success", "data": user.to_dict()}), 200


@auth_bp.route("/me", methods=["PUT"])
@jwt_required()
def update_current_user():
    user_id = int(get_jwt_identity())
    user = auth_service.get_user_by_id(user_id)
    if not user:
        return jsonify({"code": 404, "message": "User not found"}), 404
    data = request.get_json() or {}
    if "first_name" in data:
        user.first_name = data["first_name"]
    if "last_name" in data:
        user.last_name = data["last_name"]
    if "phone" in data:
        user.phone = data["phone"]
    if "address" in data:
        user.address = data["address"]
    if "password" in data and data["password"]:
        user.set_password(data["password"])
    db.session.commit()
    return jsonify({"code": 200, "message": "Profile updated", "data": user.to_dict()}), 200


@auth_bp.route("/me/recharge", methods=["POST"])
@jwt_required()
def recharge_balance():
    user_id = int(get_jwt_identity())
    user = auth_service.get_user_by_id(user_id)
    if not user:
        return jsonify({"code": 404, "message": "User not found"}), 404
    data = request.get_json() or {}
    amount = data.get("amount", 0)
    if not isinstance(amount, (int, float)) or amount <= 0:
        return jsonify({"code": 400, "message": "Amount must be a positive number"}), 400
    if amount > 10000000:
        return jsonify({"code": 400, "message": "Amount exceeds maximum (10000000)"}), 400
    user.balance += amount
    db.session.commit()
    return jsonify({
        "code": 200,
        "message": f"Recharged ¥{amount / 100:.2f}",
        "data": user.to_dict(),
    }), 200
