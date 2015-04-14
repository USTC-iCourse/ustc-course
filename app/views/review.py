from flask import Blueprint,render_template,abort,redirect,url_for,request,abort
from flask.ext.security import current_user,login_required
from app.models import Course,CourseReview
from app.forms import ReviewForm

review = Blueprint('review',__name__)


@review.route('/new/',methods=['GET','POST'])
@login_required
def new_review():
    form = ReviewForm(request.form)
    course_id = request.args.get('course_id', type=int)
    if not course_id:
        abort(404)
    course = Course.query.get(course_id)
    form = ReviewForm(request.form)
    review = CourseReview()
    if not course:
        abort(404)
    if form.validate_on_submit():
        form.populate_obj(review)
        review.author = current_user
        review.course = course
        review.add()
        return redirect(url_for('course.view_course',course_id=course_id))
    print(form.errors)
    return render_template('new-review.html', form=form, course=course)

@review.route('/edit/',methods=['GET','POST'])
@login_required
def edit_review():
    review_id = request.args.get('review_id')
    if not review_id:
        abort(404)
    review = CourseReview.query.get(review_id)
    if not review:
        abort(404)

    #check if the user is the author
    if review.author != current_user:
        return 'You have no right to do this'

    form = ReviewForm(request.form,review)
    if form.validate_on_submit():
        form.populate_obj(review)
        review.save()
        course = review.course
        return redirect(url_for('course.review', course_id=course.id, course_name=course.name))

    return render_template('new-review.html', form=form)

@review.route('/delete/',methods=['POST'])
@login_required
def delete_review():
    pass

