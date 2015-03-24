from flask_wtf import Form
from wtforms import (StringField, PasswordField, BooleanField, ValidationError)
from wtforms.validators import (InputRequired,NumberRange, Email, EqualTo)

from app.models import User

class LoginForm(Form):
    username = StringField('Username',validators=[InputRequired()])
    password = PasswordField('Password',validators=[InputRequired()])
    remember = BooleanField('Remember me',default=False)


class RegisterForm(Form):
    username = StringField('Username', validators=[InputRequired()])
    email = StringField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('password', validators=[InputRequired(),
        EqualTo('confirm_password', message='passwords must match')])
    confirm_password = PasswordField('confirm password')

    def validate_email(form, field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('The email address has been registered.')

    def validate_username(form, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('The username has been taken!')

class ForgotPasswordForm(Form):
    email = StringField('Email', validators=[InputRequired('必须输入邮箱地址'),
        Email()])

class ResetPasswordForm(Form):
    password = PasswordField('password', validators=[InputRequired(),
        EqualTo('confirm_password', message='passwords must match')])
    confirm_password = PasswordField('confirm password')


