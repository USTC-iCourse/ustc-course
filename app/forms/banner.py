from flask_wtf import FlaskForm
from wtforms import (StringField, IntegerField, RadioField, TextAreaField)

from app.models import Course

class BannerForm(FlaskForm):
    desktop = TextAreaField('desktop')
    mobile = TextAreaField('mobile')

class AnnouncementForm(FlaskForm):
    title = StringField('title')
    content = TextAreaField('content')
