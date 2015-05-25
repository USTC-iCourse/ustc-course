from flask import Blueprint,render_template,abort,redirect,url_for,request,abort,jsonify
from flask.ext.security import current_user,login_required
from app.models import Course, Review
from app.forms import ReviewForm
from app.utils import sanitize
from flask.ext.babel import gettext as _
from .course import course
import markdown

review = Blueprint('review',__name__)


@course.route('/<int:course_id>/review/',methods=['GET','POST'])
@login_required
def new_review(course_id):
    course = Course.query.get(course_id)
    if not course:
        abort(404)
    user = current_user
    review = Review.query.filter_by(course=course, author=user).first()
    if not review:
        review = Review()
        review.course = course
        review.author = user
        is_new = True
    else:
        is_new = False

    message = ''
    form = ReviewForm(request.form)
    if request.method == 'POST':
        if form.validate_on_submit():
            if form.is_mobile.data:
                form.content.data = markdown.markdown(form.content.data)
            form.content.data = sanitize(form.content.data)
            form.populate_obj(review)
            if is_new:
                review.add()
            else:
                review.save()
            return redirect(url_for('course.view_course',course_id=course_id))
        else: # invalid submission, try again
            if form.content.data:
                review.content = sanitize(form.content.data)
            if form.difficulty.data:
                review.difficulty = form.difficulty.data
            if form.homework.data:
                review.homework = form.homework.data
            if form.gain.data:
                review.gain = form.gain.data
            if form.rate.data:
                review.rate = form.rate.data
            message = '提交失败，请编辑后重新提交！'

    polls = [
        {'name': 'difficulty', 'display': '课程难度', 'options': ['简单', '中等', '困难'] },
        {'name': 'homework', 'display': '作业多少', 'options': ['不多', '中等', '超多'] },
        {'name': 'grading', 'display': '给分好坏', 'options': ['超好', '厚道', '杀手'] },
        {'name': 'gain', 'display': '收获多少', 'options': ['很多', '一般', '没有'] },
    ]
    return render_template('new-review.html', form=form, course=course, review=review, polls=polls, message=message, is_new=is_new)


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
    if review.author != current_user and not current_user.is_admin:
        message = _('You have no right to do this.')
        return jsonify(ok=ok,message=message)
    review.delete()
    ok = True
    message = _('The review has been deleted.')
    return jsonify(ok=ok,message=message)

@review.route('/comments/', methods=['GET'])
def show_comments():
    review_id = request.args.get('review_id', type=int)
    if not review_id:
        abort(404)
    review = Review.query.get(review_id)
    if not review:
        abort(404)
    return render_template('review-comments.html', review=review, user=current_user)
