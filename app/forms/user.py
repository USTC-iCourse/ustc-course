from flask_wtf import Form
from wtforms import (StringField, PasswordField, BooleanField, ValidationError)
from wtforms.validators import (InputRequired,NumberRange, Email, EqualTo)

from app.models import User
import re

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
        regex = re.compile("[a-zA-Z0-9_]+@(mail\.)?ustc\.edu\.cn")
        if not regex.fullmatch(field.data):
            raise ValidationError('必须使用科大邮箱注册!')


class ForgotPasswordForm(Form):
    email = StringField('Email', validators=[InputRequired('必须输入邮箱地址'),
        Email()])

class ResetPasswordForm(Form):
    password = PasswordField('password', validators=[InputRequired(),
        EqualTo('confirm_password', message='passwords must match')])
    confirm_password = PasswordField('confirm password')


