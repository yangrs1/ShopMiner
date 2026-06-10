import os
from app import create_app, init_db

app = create_app()

@app.cli.command("init-db")
def init_db_command():
    """Initialize database and create all tables."""
    init_db(app)
    print("Database tables created.")

if __name__ == "__main__":
    print("ShopMiner running at http://127.0.0.1:5000")
    use_reloader = os.getenv("FLASK_USE_RELOADER", "0") == "1"
    app.run(host="127.0.0.1", port=5000, debug=True, use_reloader=use_reloader)

init_db(app)  # Fallback for new environments - ensures tables exist
