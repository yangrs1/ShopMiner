from flask import Blueprint

health_bp = Blueprint("health", __name__)

from app.api.v1.health.routes import *
