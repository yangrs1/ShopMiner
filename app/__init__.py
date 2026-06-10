import os
from flask import Flask, send_from_directory, Response, request, jsonify
from app.config import config
from app.extensions import db, migrate, jwt, bcrypt, cors, limiter

# 正确的MIME类型映射
MIME_TYPES = {
    '.js': 'application/javascript',
    '.mjs': 'application/javascript',
    '.css': 'text/css',
    '.html': 'text/html',
    '.json': 'application/json',
    '.png': 'image/png',
    '.jpg': 'image/jpeg',
    '.svg': 'image/svg+xml',
    '.ico': 'image/x-icon',
    '.woff': 'font/woff',
    '.woff2': 'font/woff2',
    '.ttf': 'font/ttf',
}


def create_app(config_name="development"):
    frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
    frontend_static = os.path.join(frontend_dist, "static")
    app = Flask(__name__, static_folder=frontend_static, static_url_path="/static")

    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    bcrypt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173,http://localhost:5000,http://127.0.0.1:5000").split(",")}})
    limiter.init_app(app)
    if os.getenv("FLASK_LIMITER_ENABLED", "true").lower() == "false":
        try:
            next(iter(app.extensions["limiter"])).enabled = False
        except Exception:
            pass

    from app.api import register_blueprints
    register_blueprints(app)

    @app.before_request
    def validate_api_content_type():
        if request.path.startswith("/api/") and request.method in ("POST", "PUT", "PATCH"):
            # Allow multipart/form-data for upload endpoint
            if request.path == "/api/v1/upload":
                return
            if request.content_type is None:
                if request.content_length and request.content_length > 0:
                    return jsonify({"code": 400, "message": "Content-Type must be application/json"}), 400
            elif not request.content_type.startswith("application/json"):
                return jsonify({"code": 400, "message": "Content-Type must be application/json"}), 400

    def _send_static(dist, filename):
        """发送静态文件，确保正确的MIME类型"""
        _, ext = os.path.splitext(filename)
        mimetype = MIME_TYPES.get(ext.lower(), None)
        response = send_from_directory(dist, filename)
        if mimetype:
            if mimetype.startswith('text/') or mimetype == 'application/json':
                response.headers['Content-Type'] = f'{mimetype}; charset=utf-8'
            else:
                response.headers['Content-Type'] = mimetype
        return response

    @app.route("/")
    def index():
        return _send_static(frontend_dist, "index.html")

    @app.route("/<path:path>")
    def spa_fallback(path):
        try:
            return _send_static(frontend_dist, path)
        except Exception:
            return _send_static(frontend_dist, "index.html")

    # Serve uploaded files from project-level static/uploads/
    upload_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads"))

    @app.route("/static/uploads/<path:filename>")
    def serve_upload(filename):
        return send_from_directory(upload_dir, filename)

    return app


def init_db(app):
    with app.app_context():
        from app.models.user import User
        from app.models.product import Product
        from app.models.order import Order, OrderItem, OrderStatusLog
        from app.models.analytics import UserBehavior, RFMAnalysis, SalesPrediction
        db.create_all()

    # Ensure static/uploads/ directory exists
    upload_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "static", "uploads"))
    os.makedirs(upload_dir, exist_ok=True)
    gitkeep = os.path.join(upload_dir, ".gitkeep")
    if not os.path.exists(gitkeep):
        with open(gitkeep, "w") as f:
            f.write("")