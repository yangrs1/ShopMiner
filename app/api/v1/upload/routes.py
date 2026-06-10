import os
import uuid
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.extensions import db
from app.models.user import User

upload_bp = Blueprint("upload", __name__)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def _require_admin():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user or user.role != "admin":
        return None, jsonify({"code": 403, "message": "Admin access required"}), 403
    return user, None, None


def _validate_image(file_storage):
    """Validate file extension and image magic bytes."""
    filename = file_storage.filename or ""
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    if ext not in ALLOWED_EXTENSIONS:
        return False

    # Read header bytes to verify image type (magic byte check)
    file_storage.seek(0)
    header = file_storage.read(32)
    file_storage.seek(0)

    if ext in (".jpg", ".jpeg"):
        if not header.startswith(b"\xff\xd8"):
            return False
    elif ext == ".png":
        if not header.startswith(b"\x89PNG"):
            return False
    elif ext == ".gif":
        if not header.startswith(b"GIF8"):
            return False
    elif ext == ".webp":
        if not (header.startswith(b"RIFF") and header[8:12] == b"WEBP"):
            return False

    return True


@upload_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_file():
    user, error_response, status_code = _require_admin()
    if error_response:
        return error_response, status_code

    if "file" not in request.files:
        return jsonify({"code": 400, "message": "No file provided"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"code": 400, "message": "No file selected"}), 400

    # Check file size before processing
    file.seek(0, os.SEEK_END)
    size = file.tell()
    file.seek(0)

    if size > MAX_FILE_SIZE:
        return jsonify({"code": 400, "message": "File too large. Max 5MB"}), 400

    # Validate image type (extension + magic bytes)
    if not _validate_image(file):
        return jsonify({"code": 400, "message": "Invalid file type. Allowed: jpg, png, gif, webp"}), 400

    # Generate unique filename
    _, ext = os.path.splitext(file.filename.lower())
    unique_name = f"{uuid.uuid4().hex}{ext}"

    # Save to static/uploads/ (project root)
    upload_dir = os.path.normpath(os.path.join(current_app.root_path, "..", "static", "uploads"))
    os.makedirs(upload_dir, exist_ok=True)

    file_path = os.path.join(upload_dir, unique_name)
    file.save(file_path)

    return jsonify({
        "code": 200,
        "message": "success",
        "data": {
            "url": f"/static/uploads/{unique_name}",
        },
    }), 200
