import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me")
    uri = os.environ.get("DATABASE_URL", "sqlite:///helpdesk.db")
    # Normalize older Heroku-style URLs
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    csrf.init_app(app)

    # Blueprints
    from .public import public_bp
    from .auth import auth_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)

    # Ensure tables exist on first boot (handy for fresh deploys)
    with app.app_context():
        db.create_all()

    return app
