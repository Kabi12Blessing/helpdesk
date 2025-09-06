import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect

db = SQLAlchemy()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "change-me")

    # DB URL (supports postgres:// and postgresql://)
    uri = os.environ.get("DATABASE_URL", "sqlite:///helpdesk.db")
    if uri.startswith("postgres://"):
        uri = uri.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)
    csrf.init_app(app)

    # Register blueprints
    from .public import public_bp
    from .auth import auth_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)

    # Ensure tables exist and optionally create an admin on first boot
    with app.app_context():
        from .models import User  # import here to avoid circulars
        db.create_all()

        admin_email = os.environ.get("ADMIN_EMAIL")
        admin_password = os.environ.get("ADMIN_PASSWORD")
        if admin_email and admin_password:
            u = User.query.filter_by(email=admin_email.strip().lower()).first()
            if not u:
                u = User(email=admin_email.strip().lower(), role="admin")
                u.set_password(admin_password.strip())
                db.session.add(u)
                db.session.commit()

    return app

