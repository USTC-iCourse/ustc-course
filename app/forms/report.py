from flask_wtf import Form
from wtforms import (StringField, PasswordField,TextAreaField, BooleanField, ValidationError)
from wtforms.validators import (InputRequired,NumberRange, Email, EqualTo)

class ReportBugForm(Form):
    url = StringField('Url',[InputRequired()])
    description = TextAreaField('Description')
    browser = StringField('Browser')
    os = StringField('Operating System')
    email = StringField('Email')
    username = StringField('Username')

