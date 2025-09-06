import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_talisman import Talisman
from dotenv import load_dotenv

db = SQLAlchemy()
csrf = CSRFProtect()

def create_app():
    load_dotenv()
    app = Flask(__name__)

    # Config
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///helpdesk.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Init extensions
    db.init_app(app)
    csrf.init_app(app)

    # Basic security headers (CSP/HSTS)
    csp = {
        "default-src": "'self'",
        "style-src": "'self' 'unsafe-inline'",
        "script-src": "'self'",
        "img-src": "'self' data:",
    }
    Talisman(app, content_security_policy=csp)

    # Register blueprints (routes live here)
    from .public import public_bp
    from .auth import auth_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)

    # Create tables on first run
    with app.app_context():
        db.create_all()

    # Simple health check
    @app.get("/health")
    def health():
        return "ok", 200

    return app
