def register_blueprints(app):
    from app.api.v1.health.routes import health_bp
    from app.api.v1.auth.routes import auth_bp
    from app.api.v1.product.routes import product_bp
    from app.api.v1.order.routes import order_bp
    from app.api.v1.cart.routes import cart_bp
    from app.api.v1.favorites.routes import favorites_bp
    from app.api.v1.admin.routes import admin_bp
    from app.api.v1.analytics.routes import analytics_bp
    from app.api.v1.upload.routes import upload_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp, url_prefix="/api/v1/auth")
    app.register_blueprint(product_bp, url_prefix="/api/v1")
    app.register_blueprint(order_bp, url_prefix="/api/v1")
    app.register_blueprint(cart_bp, url_prefix="/api/v1")
    app.register_blueprint(favorites_bp, url_prefix="/api/v1")
    app.register_blueprint(admin_bp, url_prefix="/api/v1")
    app.register_blueprint(analytics_bp, url_prefix="/api/v1")
    app.register_blueprint(upload_bp, url_prefix="/api/v1")