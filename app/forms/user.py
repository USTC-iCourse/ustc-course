from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField, ValidationError, TextAreaField, FileField, SelectField)
from wtforms.validators import (DataRequired,NumberRange, Email, EqualTo, Length, Optional, AnyOf)
from app.models import User
from flask_login import current_user
from flask_babel import gettext as _
from app.utils import EMAIL_DOMAIN_IDENTITY, validate_username, validate_email_parts
import re

def strip_username(input_s):
    strip_p = re.compile('\s+')
    return strip_p.sub('',input_s)

class UsernameField(StringField):
    ''' a cumstom field of username '''
    def process_data(self,value):
        if value:
            self.data = strip_username(value)
        else:
            self.data = value

class LoginForm(FlaskForm):
    username = UsernameField('Username',validators=[DataRequired()])
    password = PasswordField('Password',validators=[DataRequired()])
    remember = BooleanField('Remember me',default=False)


# Labelled by identity rather than by domain, because the identity is what the
# person knows about themselves and the domain is merely how the site encodes
# it.  Order matters: the student domain is the default and comes first.
EMAIL_DOMAIN_CHOICES = [
    ('mail.ustc.edu.cn', '学生（@mail.ustc.edu.cn）'),
    ('ustc.edu.cn', '教师 / 职工（@ustc.edu.cn）'),
]


class UstcEmailForm(FlaskForm):
    '''Collects a USTC address as a prefix plus a chosen domain.

    A single email box let a student register as a teacher by leaving out four
    characters, and the resulting account could never be activated.  Splitting
    the field makes the domain unmistypeable and puts the identity it implies
    in front of the person choosing it.
    '''
    email_domain = SelectField('Email domain',
        default=EMAIL_DOMAIN_CHOICES[0][0],
        choices=EMAIL_DOMAIN_CHOICES,
        validators=[DataRequired('请选择身份'),
                    AnyOf([choice[0] for choice in EMAIL_DOMAIN_CHOICES],
                          message='请选择身份')])
    email_prefix = StringField('Email prefix',
        validators=[DataRequired('必须填写邮箱前缀')])

    @property
    def email_address(self):
        return (self.email_prefix.data or '').strip() + '@' + (self.email_domain.data or '')

    def validate_email_prefix(form, field):
        res = validate_email_parts(field.data, form.email_domain.data)
        if res == 'OK':
            return True
        else:
            raise ValidationError(res)


class RegisterForm(UstcEmailForm):
    username = UsernameField('Username', validators=[DataRequired(), Length(max=30,message='The length must under 30')])
    password = PasswordField('password', validators=[DataRequired(),
        EqualTo('confirm_password', message='passwords must match')])
    confirm_password = PasswordField('confirm password')

    def validate_username(form, field):
        res = validate_username(field.data)
        if res == 'OK':
            return True
        else:
            raise ValidationError(res)


class FixUnconfirmedEmailForm(UstcEmailForm):
    '''Move the address of an account that was never activated.

    Registering again is not a way out of a mistyped domain: the username is
    held by the account carrying the wrong address, so the person has to invent
    a second name and abandon the first account.  Correcting the address in
    place keeps the name.  It demands the account password and the view refuses
    once the account is confirmed, so it cannot be used to take over an
    address that somebody is actually reading.
    '''
    login = StringField('Username or email',
        validators=[DataRequired('请填写原来的用户名或邮箱')])
    password = PasswordField('Password', validators=[DataRequired('请填写密码')])

class PasswordForm(FlaskForm):
    old_password = PasswordField('Old password',validators=[DataRequired()])
    password = PasswordField('password', validators=[DataRequired(),
        EqualTo('confirm_password', message='passwords must match')])
    confirm_password = PasswordField('confirm password')
    def validate_old_password(form,field):
        if not current_user.check_password(field.data):
            raise ValidationError('Verify password failed')


class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired('必须输入邮箱地址'),
        Email()])

class ResetPasswordForm(FlaskForm):
    password = PasswordField('password', validators=[DataRequired(),
        EqualTo('confirm_password', message='passwords must match')])
    confirm_password = PasswordField('confirm password')


class ProfileForm(FlaskForm):
    username = UsernameField('Username', validators=[DataRequired(),Length(max=30,message='The length must under 30')])
    #gender = SelectField('Gender',choices=[('male',_('male')),('female',_('female')),('unkown',_('unkown'))],validators=[DataRequired()])
    description = TextAreaField('Description', validators=[Optional(),Length(max=1024, message='长度不大于1024')])
    homepage = StringField('Homepage', validators=[Optional(),Length(max=200,message="长度不大于200")])
    avatar = FileField('Avatar', validators=[])
    is_following_hidden = BooleanField('is_following_hidden', default=False)
    is_profile_hidden = BooleanField('is_profile_hidden', default=False)

    def validate_username(form, field):
        res = validate_username(field.data, check_db=False)
        if res == 'OK':
            return True
        else:
            raise ValidationError(res)


class TeacherProfileForm(FlaskForm):
    description = TextAreaField('Description', validators=[Optional(),Length(max=1024)])
    homepage = StringField('Homepage', validators=[Optional(),Length(max=200,message="长度不大于200")])
    research_interest = StringField('Research_Interest', validators=[Optional(), Length(max=200, message="长度不大于200")])
    avatar = FileField('Avatar', validators=[])

