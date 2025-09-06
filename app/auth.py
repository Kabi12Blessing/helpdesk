from datetime import datetime
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, request, session, Response
from sqlalchemy import or_
from .forms import LoginForm, AssignToMeForm, CommentForm, StatusForm
from .models import User, Ticket, Comment
from . import db

auth_bp = Blueprint("auth", __name__)

def current_user():
    uid = session.get("user_id")
    return User.query.get(uid) if uid else None

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

def _sla_text(ticket: Ticket) -> str:
    """Return a human-readable first-response SLA countdown (or 'Met' / '—')."""
    due = ticket.first_response_due_at
    met = ticket.first_response_met_at
    if not due:
        return "—"
    if met:
        return "Met"
    now = datetime.utcnow()
    delta = int((due - now).total_seconds())
    if delta > 0:
        h = delta // 3600
        m = (delta % 3600) // 60
        return f"{h}h {m}m left" if h else f"{m}m left"
    delta = abs(delta)
    h = delta // 3600
    m = (delta % 3600) // 60
    return f"Breached {h}h {m}m" if h else f"Breached {m}m"

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.strip().lower()).first()
        if user and user.verify_password(form.password.data):
            session["user_id"] = user.id
            session["role"] = user.role
            nxt = request.args.get("next") or url_for("auth.agent_queue")
            return redirect(nxt)
    return render_template("login.html", form=form, title="Log in")

@auth_bp.get("/logout")
def logout():
    session.pop("user_id", None)
    session.pop("role", None)
    return redirect(url_for("auth.login"))

@auth_bp.get("/agent/queue")
@login_required
def agent_queue():
    user = current_user()
    f = request.args.get("f", "all")  # all | unassigned | mine | P1|P2|P3|P4
    qtext = (request.args.get("q") or "").strip()

    q = Ticket.query
    if f == "unassigned":
        q = q.filter(Ticket.assignee_id.is_(None))
    elif f == "mine":
        q = q.filter(Ticket.assignee_id == user.id)
    elif f in {"P1", "P2", "P3", "P4"}:
        q = q.filter(Ticket.priority == f)

    if qtext:
        like = f"%{qtext}%"
        q = q.filter(or_(
            Ticket.requester_name.ilike(like),
            Ticket.requester_email.ilike(like),
            Ticket.description.ilike(like),
            Ticket.category.ilike(like)
        ))

    tickets = q.order_by(Ticket.created_at.desc()).all()
    form = AssignToMeForm()
    user_map = {u.id: u.email for u in User.query.all()}
    sla_map = {t.id: _sla_text(t) for t in tickets}

    return render_template(
        "agent_queue.html",
        tickets=tickets,
        user=user,
        user_map=user_map,
        form=form,
        f=f,
        q=qtext,
        sla_map=sla_map,
        title="Agent queue"
    )

@auth_bp.post("/agent/assign")
@login_required
def assign_to_me():
    form = AssignToMeForm()
    if form.validate_on_submit():
        try:
            tid = int(form.ticket_id.data)
        except Exception:
            return redirect(url_for("auth.agent_queue"))
        t = Ticket.query.get(tid)
        if t:
            t.assignee_id = session["user_id"]
            db.session.commit()
    return redirect(url_for("auth.agent_queue"))

# -------- Ticket detail & actions --------

@auth_bp.get("/agent/ticket/<int:ticket_id>")
@login_required
def ticket_detail(ticket_id):
    user = current_user()
    t = Ticket.query.get_or_404(ticket_id)
    comments = Comment.query.filter_by(ticket_id=t.id).order_by(Comment.created_at.asc()).all()
    user_map = {u.id: u.email for u in User.query.all()}

    comment_form = CommentForm()
    status_form = StatusForm()
    status_form.status.data = t.status

    return render_template(
        "ticket_detail.html",
        t=t,
        comments=comments,
        comment_form=comment_form,
        status_form=status_form,
        user=user,
        user_map=user_map,
        title=f"Ticket #{t.id}"
    )

@auth_bp.post("/agent/ticket/<int:ticket_id>/comment")
@login_required
def ticket_post_comment(ticket_id):
    t = Ticket.query.get_or_404(ticket_id)
    form = CommentForm()
    if form.validate_on_submit():
        visibility = form.visibility.data if form.visibility.data in {"public","internal"} else "public"
        c = Comment(
            ticket_id=t.id,
            author_id=session.get("user_id"),
            visibility=visibility,
            body=form.body.data.strip()
        )
        db.session.add(c)
        if visibility == "public" and not t.first_response_met_at:
            t.first_response_met_at = datetime.utcnow()
        db.session.commit()
    return redirect(url_for("auth.ticket_detail", ticket_id=t.id))

@auth_bp.post("/agent/ticket/<int:ticket_id>/status")
@login_required
def ticket_change_status(ticket_id):
    t = Ticket.query.get_or_404(ticket_id)
    form = StatusForm()
    if form.validate_on_submit():
        t.status = form.status.data
        db.session.commit()
    return redirect(url_for("auth.ticket_detail", ticket_id=t.id))

# -------- Dashboard --------

@auth_bp.get("/admin/dashboard")
@login_required
def admin_dashboard():
    now = datetime.utcnow()
    sod = now.replace(hour=0, minute=0, second=0, microsecond=0)

    open_statuses = ["Open", "In Progress", "Waiting on Requester"]
    new_today = Ticket.query.filter(Ticket.created_at >= sod).count()
    open_count = Ticket.query.filter(Ticket.status.in_(open_statuses)).count()

    total_with_due = Ticket.query.filter(Ticket.first_response_due_at.isnot(None)).count()
    met_on_time = Ticket.query.filter(
        Ticket.first_response_due_at.isnot(None),
        Ticket.first_response_met_at.isnot(None),
        Ticket.first_response_met_at <= Ticket.first_response_due_at
    ).count()

    def pct(a, b):
        return round((a / b) * 100) if b else None

    overall_pct = pct(met_on_time, total_with_due)

    by_priority = {}
    for p in ["P1","P2","P3","P4"]:
        total_p = Ticket.query.filter(
            Ticket.priority == p, Ticket.first_response_due_at.isnot(None)
        ).count()
        met_p = Ticket.query.filter(
            Ticket.priority == p,
            Ticket.first_response_due_at.isnot(None),
            Ticket.first_response_met_at.isnot(None),
            Ticket.first_response_met_at <= Ticket.first_response_due_at
        ).count()
        by_priority[p] = {"total": total_p, "met": met_p, "pct": pct(met_p, total_p)}

    user = current_user()
    return render_template(
        "dashboard.html",
        user=user,
        new_today=new_today,
        open_count=open_count,
        overall_met=met_on_time,
        overall_total=total_with_due,
        overall_pct=overall_pct,
        by_priority=by_priority,
        title="Dashboard"
    )

# -------- Export CSV (respects same filters + search) --------

@auth_bp.get("/agent/export.csv")
@login_required
def agent_export_csv():
    from io import StringIO
    import csv

    user = current_user()
    f = request.args.get("f", "all")
    qtext = (request.args.get("q") or "").strip()

    q = Ticket.query
    if f == "unassigned":
        q = q.filter(Ticket.assignee_id.is_(None))
    elif f == "mine":
        q = q.filter(Ticket.assignee_id == user.id)
    elif f in {"P1","P2","P3","P4"}:
        q = q.filter(Ticket.priority == f)

    if qtext:
        like = f"%{qtext}%"
        q = q.filter(or_(
            Ticket.requester_name.ilike(like),
            Ticket.requester_email.ilike(like),
            Ticket.description.ilike(like),
            Ticket.category.ilike(like)
        ))

    tickets = q.order_by(Ticket.created_at.desc()).all()
    user_map = {u.id: u.email for u in User.query.all()}

    def fmt(dt):
        return dt.strftime("%Y-%m-%d %H:%M") if dt else ""

    sio = StringIO()
    w = csv.writer(sio)
    w.writerow([
        "id","priority","category","requester_name","requester_email",
        "status","assignee","created_at","first_response_due_at","first_response_met_at","sla"
    ])
    for t in tickets:
        assignee = user_map.get(t.assignee_id, "")
        w.writerow([
            t.id, t.priority, t.category, t.requester_name, t.requester_email,
            t.status, assignee, fmt(t.created_at), fmt(t.first_response_due_at),
            fmt(t.first_response_met_at), _sla_text(t)
        ])

    csv_data = sio.getvalue()
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=queue_export.csv"}
    )
