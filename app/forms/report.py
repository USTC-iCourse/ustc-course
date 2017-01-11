from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField,TextAreaField, BooleanField, ValidationError)
from wtforms.validators import (InputRequired,NumberRange, Email, EqualTo)

class ReportBugForm(FlaskForm):
    url = StringField('Url',[InputRequired()])
    description = TextAreaField('Description')
    browser = StringField('Browser')
    os = StringField('Operating System')
    email = StringField('Email')
    username = StringField('Username')

