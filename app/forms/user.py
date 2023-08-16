from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, BooleanField, ValidationError, TextAreaField, FileField, SelectField)
from wtforms.validators import (DataRequired, NumberRange, Email, EqualTo, Length, Optional, AnyOf)
from app.models import User
from flask_login import current_user
from flask_babel import gettext as _
from app.utils import validate_username, validate_email
import re


def strip_username(input_s):
  strip_p = re.compile('\s+')
  return strip_p.sub('', input_s)


class UsernameField(StringField):
  ''' a cumstom field of username '''

  def process_data(self, value):
    if value:
      self.data = strip_username(value)
    else:
      self.data = value


class LoginForm(FlaskForm):
  username = UsernameField('Username', )
  password = PasswordField('Password', )
  remember = BooleanField('Remember me', default=True)


class RegisterForm(FlaskForm):
  username = UsernameField('Username', validators=[DataRequired(), Length(max=30, message='The length must under 30')])
  email = StringField('Email', validators=[DataRequired(), Email()])
  password = PasswordField('password', validators=[DataRequired(),
                                                   EqualTo('confirm_password', message='passwords must match')])
  confirm_password = PasswordField('confirm password')

  def validate_email(form, field):
    res = validate_email(field.data)
    if res == 'OK':
      return True
    else:
      raise ValidationError(res)

  def validate_username(form, field):
    res = validate_username(field.data)
    if res == 'OK':
      return True
    else:
      raise ValidationError(res)


class ProfileForm(FlaskForm):
  username = UsernameField('Username', validators=[DataRequired(), Length(max=30, message='The length must under 30')])
  # gender = SelectField('Gender',choices=[('male',_('male')),('female',_('female')),('unkown',_('unkown'))],validators=[DataRequired()])
  description = TextAreaField('Description', validators=[Optional(), Length(max=1024, message='长度不大于1024')])
  homepage = StringField('Homepage', validators=[Optional(), Length(max=200, message="长度不大于200")])
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
  description = TextAreaField('Description', validators=[Optional(), Length(max=1024)])
  homepage = StringField('Homepage', validators=[Optional(), Length(max=200, message="长度不大于200")])
  research_interest = StringField('Research_Interest',
                                  validators=[Optional(), Length(max=200, message="长度不大于200")])
  avatar = FileField('Avatar', validators=[])
