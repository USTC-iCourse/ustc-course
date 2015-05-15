from flask import Blueprint,render_template,abort,redirect,url_for,request,abort,jsonify
from flask.ext.security import current_user,login_required
from app.models import Course, Review
from app.forms import ReviewForm
from app.utils import sanitize
from flask.ext.babel import gettext as _
from .course import course

review = Blueprint('review',__name__)


@course.route('/<int:course_id>/review/new/',methods=['GET','POST'])
@login_required
def new_review(course_id):
    course = Course.query.get(course_id)
    if not course:
        abort(404)
    user = current_user
    review = Review.query.filter_by(course=course, author=user)
    if not review:
        review = Review()
        review.course = course
        review.author = user
        is_new = True
    else:
        is_new = False

    form = ReviewForm(request.form)
    if form.validate_on_submit():
        form.content.data = sanitize(form.content.data)
        form.populate_obj(review)
        if is_new:
            review.add()
        else:
            review.save()
        return redirect(url_for('course.view_course',course_id=course_id))
    return render_template('new-review.html', form=form, course=course, review=review)


@review.route('/delete/',methods=['POST'])
@login_required
def delete_review():
    review_id = request.form.get('id',type=int)
    if not review_id:
        message = _('You must specify a id.')
        return jsonify(ok=ok,message=message)
    review = Review.query.get(review_id)
    ok = False
    message = _('Something wrong happend.')
    if not review:
        message = _('Can\'t find the review.')
        return jsonify(ok=ok,message=message)
    #check if the user is the author
    if review.author != current_user:
        message = _('You have no right to do this.')
        return jsonify(ok=ok,message=message)
    review.delete()
    ok = True
    message = _('The review has been deleted.')
    return jsonify(ok=ok,message=message)

