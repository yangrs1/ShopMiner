from datetime import datetime
from flask import jsonify
from app.api.v1.health import health_bp
from app.extensions import db


@health_bp.route("/api/v1/health", methods=["GET"])
def health_check():
    db_status = "disconnected"
    try:
        db.session.execute(db.text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return jsonify({
        "status": "healthy" if db_status == "connected" else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "database": db_status,
    })
