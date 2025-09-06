from datetime import datetime
from . import db
from passlib.hash import bcrypt

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="agent")  # 'agent' or 'admin'
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = bcrypt.hash(password)

    def verify_password(self, password):
        return bcrypt.verify(password, self.password_hash)

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    requester_name = db.Column(db.String(120), nullable=False)
    requester_email = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    priority = db.Column(db.String(2), nullable=False)  # P1..P4
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(30), nullable=False, default="Open")
    assignee_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # who owns it
    # --- SLA fields ---
    first_response_due_at = db.Column(db.DateTime, nullable=True)
    first_response_met_at = db.Column(db.DateTime, nullable=True)
    # ---
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

# --- Ticket comments (public replies & internal notes) ---
class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ticket_id = db.Column(db.Integer, db.ForeignKey('ticket.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # None for requester-side later
    visibility = db.Column(db.String(10), nullable=False, default="public")     # 'public' or 'internal'
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


