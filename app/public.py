from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for, request
from .forms import SubmitRequestForm, CheckStatusForm
from .models import Ticket, Comment
from . import db

public_bp = Blueprint("public", __name__)

def compute_first_response_due(priority: str, start: datetime) -> datetime:
    """Naive SLA: P1=1h, P2=4h, P3=24h, P4=48h."""
    mapping = {"P1": timedelta(hours=1),
               "P2": timedelta(hours=4),
               "P3": timedelta(days=1),
               "P4": timedelta(days=2)}
    return start + mapping.get(priority, timedelta(days=2))

@public_bp.get("/")
def home():
    return redirect(url_for("public.submit_request"))

@public_bp.route("/submit", methods=["GET", "POST"])
def submit_request():
    form = SubmitRequestForm()
    if form.validate_on_submit():
        now = datetime.utcnow()
        t = Ticket(
            requester_name=form.requester_name.data.strip(),
            requester_email=form.requester_email.data.strip(),
            category=form.category.data,
            priority=form.priority.data,
            description=form.description.data.strip(),
            status="Open",
            first_response_due_at=compute_first_response_due(form.priority.data, now),
        )
        db.session.add(t)
        db.session.commit()
        return redirect(url_for("public.confirm", ticket_id=t.id))
    return render_template("submit_request.html", form=form, title="Submit a request")

@public_bp.get("/confirm/<int:ticket_id>")
def confirm(ticket_id):
    return render_template("confirm.html", ticket_id=ticket_id, title="Request received")

# TEMP: verify tickets exist
@public_bp.get("/_admin/tickets")
def admin_tickets():
    tickets = Ticket.query.order_by(Ticket.created_at.desc()).all()
    return render_template("tickets_list.html", tickets=tickets, title="All tickets (temp)")

# ---- Public status check (Ticket ID + Email) ----
@public_bp.route("/status", methods=["GET", "POST"])
def check_status():
    form = CheckStatusForm()
    ticket = None
    public_comments = []
    if form.validate_on_submit():
        # Find ticket by ID, then verify the email matches (case-insensitive)
        try:
            tid = int(form.ticket_id.data)
        except Exception:
            tid = None
        if tid:
            t = Ticket.query.get(tid)
            if t and t.requester_email.strip().lower() == form.requester_email.data.strip().lower():
                ticket = t
                public_comments = (Comment.query
                                   .filter_by(ticket_id=t.id, visibility="public")
                                   .order_by(Comment.created_at.asc())
                                   .all())
    return render_template("status_check.html",
                           form=form,
                           ticket=ticket,
                           public_comments=public_comments,
                           title="Check ticket status")
