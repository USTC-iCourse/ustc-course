from flask_wtf import FlaskForm
from wtforms import (StringField, IntegerField, RadioField, TextAreaField, BooleanField)
from wtforms.validators import (InputRequired,NumberRange)

from app.models import Review

class ReviewForm(FlaskForm):
    term = IntegerField('term',validators=[InputRequired()])
    difficulty = IntegerField('grading',validators=[InputRequired(),NumberRange(1,3)])
    homework = IntegerField('homework',validators=[InputRequired(),NumberRange(1,3)])
    grading = IntegerField('grading',validators=[InputRequired(),NumberRange(1,3)])
    gain = IntegerField('gain',validators=[InputRequired(),NumberRange(1,3)])
    rate = IntegerField('rate',validators=[InputRequired(),NumberRange(1,10)])
    content = TextAreaField('content',validators=[InputRequired()])
    is_anonymous = BooleanField('is_anonymous', default=False)
    only_visible_to_student = BooleanField('only_visible_to_student', default=False)
    is_mobile = IntegerField('is_mobile', default=False)
    is_ajax = BooleanField('is_ajax', default=False)

class ReviewCommentForm(FlaskForm):
    review_id = IntegerField('review id',validators=[InputRequired()])
    content = TextAreaField('content', validators=[InputRequired()])

