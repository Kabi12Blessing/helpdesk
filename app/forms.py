from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms import PasswordField
from wtforms.validators import DataRequired, Email, Length

class SubmitRequestForm(FlaskForm):
    requester_name = StringField("Your name", validators=[DataRequired(), Length(max=120)])
    requester_email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    category = SelectField(
        "Category",
        choices=[("it","IT issue"), ("access","Account access"), ("equipment","Equipment"), ("other","Other")],
        validators=[DataRequired()],
    )
    priority = SelectField(
        "Priority",
        choices=[("P1","P1 - Critical"), ("P2","P2 - High"), ("P3","P3 - Medium"), ("P4","P4 - Low")],
        validators=[DataRequired()],
    )
    description = TextAreaField("Describe the issue", validators=[DataRequired(), Length(max=2000)])
    submit = SubmitField("Submit")

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=120)])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6, max=128)])
    submit = SubmitField("Log in")

from wtforms import HiddenField

class AssignToMeForm(FlaskForm):
    ticket_id = HiddenField(validators=[DataRequired()])
    submit = SubmitField("Assign to me")

from wtforms import TextAreaField

class CommentForm(FlaskForm):
    visibility = SelectField(
        "Visibility",
        choices=[("public", "Public reply (requester can see)"),
                 ("internal", "Internal note (agents only)")],
        validators=[DataRequired()],
    )
    body = TextAreaField("Message", validators=[DataRequired(), Length(max=4000)])
    submit = SubmitField("Post")

class StatusForm(FlaskForm):
    status = SelectField(
        "Change status",
        choices=[
            ("Open","Open"),
            ("In Progress","In Progress"),
            ("Waiting on Requester","Waiting on Requester"),
            ("Resolved","Resolved"),
            ("Closed","Closed"),
        ],
        validators=[DataRequired()],
    )
    submit = SubmitField("Update")

class CheckStatusForm(FlaskForm):
    ticket_id = StringField("Ticket ID", validators=[DataRequired(), Length(max=10)])
    requester_email = StringField("Email used on the request", validators=[DataRequired(), Email(), Length(max=120)])
    submit = SubmitField("Check status")
