from flask_wtf import FlaskForm
from wtforms import (StringField, IntegerField, RadioField, TextAreaField)
from wtforms.validators import (InputRequired,NumberRange, Length)

from app.models import Course

class CourseForm(FlaskForm):
    #cno = StringField('cno',validators=[InputRequired(), Length(max=20)])
    #term = StringField('term', validators=[InputRequired(), Length(max=20)])
    #name = StringField('name',validators=[InputRequired(), Length(max=80)])
    #dept = StringField('dept', validators=[Length(max=80)])
    homepage = StringField('homepage')
    #description = TextAreaField('description')
    introduction = TextAreaField('introduction')
    #credit = IntegerField('credit')
    #hours = IntegerField('hours')
    #default_classes = StringField('classes',validators=[Length(max=200)])
    #start_end_week = StringField('start_end_week',validators=[Length(max=100)])
    #time_location = StringField('time_location', validators=[Length(max=100)])


