from flask import Blueprint,render_template,abort,redirect,url_for,request,abort
from flask.ext.security import current_user,login_required
from app.models import Course, Review
from app.forms import ReviewForm

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
        form.populate_obj(review)
        review.author = current_user
        review.course = course
        review.add()
        return redirect(url_for('course.view_course',course_id=course_id))
    print(form.errors)
    return render_template('new-review.html', form=form, course=course)

@review.route('/edit/<int:review_id>',methods=['GET','POST'])
@login_required
def edit_review(review_id):
    review = Review.query.get(review_id)
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

