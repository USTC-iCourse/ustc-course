from flask_wtf import Form
from wtforms import (StringField, PasswordField, BooleanField, ValidationError, TextAreaField, FileField)
from wtforms.validators import (InputRequired,NumberRange, Email, EqualTo, Length, Optional)
from app.models import User
from flask.ext.login import current_user
import re

RESERVED_USERNAME = set(['管理员',
    'Administrator'])

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
        regex = re.compile("[a-zA-Z0-9_]+@(mail\.)?ustc\.edu\.cn")
        if not regex.fullmatch(field.data):
            raise ValidationError('必须使用科大邮箱注册!')
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('The email address has been registered.')

    def validate_username(form, field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('The username has been taken!')
        if field.data in RESERVED_USERNAME:
            raise ValidationError('The username is reserved!')

class PasswordForm(Form):
    old_password = PasswordField('Old password',validators=[InputRequired()])
    password = PasswordField('password', validators=[InputRequired(),
        EqualTo('confirm_password', message='passwords must match')])
    confirm_password = PasswordField('confirm password')
    def validate_old_password(form,field):
        if not current_user.check_password(field.data):
            raise ValidationError('Verify password failed')


class ForgotPasswordForm(Form):
    email = StringField('Email', validators=[InputRequired('必须输入邮箱地址'),
        Email()])

class ResetPasswordForm(Form):
    password = PasswordField('password', validators=[InputRequired(),
        EqualTo('confirm_password', message='passwords must match')])
    confirm_password = PasswordField('confirm password')

class ProfileForm(Form):
    username = StringField('Username', validators=[InputRequired()])
    description = TextAreaField('Description', validators=[Optional(),Length(max=1024)])
    homepage = StringField('Homepage', validators=[Optional(),Length(max=200,message="长度不大于200")])
    avatar = FileField('Avatar', validators=[])

    def validate_username(form,field):
        if field.data!=current_user.username and User.query.filter_by(username=field.data).first():
            raise ValidationError('The username has been taken!')
        if field.data in RESERVED_USERNAME:
            raise ValidationError('The username is reserved!')
