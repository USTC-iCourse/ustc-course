from flask import Blueprint,render_template,abort,redirect,url_for,request,abort,jsonify
from flask.ext.security import current_user,login_required
from app.models import Course, Review
from app.forms import ReviewForm
from app.utils import sanitize

review = Blueprint('review',__name__)


@review.route('/new/<int:course_id>',methods=['GET','POST'])
@login_required
def new_review(course_id):
    course = Course.query.get(course_id)
    if not course:
        abort(404)
    form = ReviewForm(request.form)
    review = Review()
    if form.validate_on_submit():
        form.content.data = sanitize(form.content.data)
        form.populate_obj(review)
        review.author = current_user
        review.course = course
        review.add()
        return redirect(url_for('course.view_course',course_id=course_id))
    return render_template('new-review.html', form=form, course=course)

@review.route('/edit/<int:review_id>',methods=['GET','POST'])
@login_required
def edit_review(review_id):
    review = Review.query.get(review_id)
    if not review:
        abort(404)

    #check if the user is the author
    if review.author != current_user:
        return _('You have no right to do this')

    form = ReviewForm(request.form,review)
    if form.validate_on_submit():
        new_review = Review()
        form.content.data = sanitize(form.content.data)
        form.populate_obj(new_review)
        review.update(new_review)
        course = review.course
        return redirect(url_for('course.view_course', course_id=course.id, course_name=course.name))

    course = review.course
    return render_template('edit-review.html', form=form,review_id=review_id, course=course)

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

