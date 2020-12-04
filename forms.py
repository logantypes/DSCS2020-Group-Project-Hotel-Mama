from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField, PasswordField, FileField, DateTimeField
from wtforms.validators import DataRequired


class RegistrationForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit_button = SubmitField("Submit")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit_button = SubmitField("Submit")
