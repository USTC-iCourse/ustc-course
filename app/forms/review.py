from flask_wtf import Form
from wtforms import (StringField, IntegerField, RadioField, TextAreaField)
from wtforms.validators import (InputRequired,NumberRange)

from app.models import Review

class ReviewForm(Form):
    difficulty = IntegerField('grading',validators=[InputRequired(),NumberRange(1,3)])
    homework = IntegerField('homework',validators=[InputRequired(),NumberRange(1,3)])
    grading = IntegerField('grading',validators=[InputRequired(),NumberRange(1,3)])
    gain = IntegerField('gain',validators=[InputRequired(),NumberRange(1,3)])
    rate = IntegerField('rate',validators=[InputRequired(),NumberRange(1,10)])
    content = TextAreaField('content',validators=[InputRequired()])

class ReviewCommentForm(Form):
    review_id = IntegerField('review id',validators=[InputRequired()])
    content = TextAreaField('content', validators=[InputRequired()])

