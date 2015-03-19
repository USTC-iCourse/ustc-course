from flask_wtf import Form
from wtforms import (StringField, IntegerField, RadioField, TextAreaField)
from wtforms.validators import (InputRequired,NumberRange)

from app.models import CourseReview

class ReviewForm(Form):
    rate = IntegerField('rate',validators=[InputRequired,NumberRange(1,10)])
    title = StringField('title',validators=[InputRequired])
    content = TextAreaField('content',validators=[InputRequired])
