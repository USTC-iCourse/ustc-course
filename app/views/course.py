from flask import Blueprint,render_template,abort,redirect,url_for,request,abort,jsonify
from flask.ext.login import login_required
from app.models import Course,CourseRate
from app.forms import ReviewForm

course = Blueprint('course',__name__)
QUERY_ORDER = [Course.term.desc(),
        Course.kcid,
        ]

@course.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    courses_page = Course.query.order_by(*QUERY_ORDER).paginate(page,per_page=per_page)
    return render_template('course-index.html',pagination=courses_page)

@course.route('/<int:course_id>/')
def view_course(course_id,course_name=None):
    course = Course.query.get(course_id)
    if not course:
        abort(404)

    related_courses = Course.query.filter_by(name=course_name).all()
    teacher = course.teacher
    reviews = course.reviews.all()
    if teacher:
        same_teacher_courses = teacher.courses
    else:
        same_teacher_courses = None
    return render_template('course.html',
            course=course,
            course_rate = course.course_rate,
            reviews=reviews,
            related_courses=related_courses,
            teacher=teacher,
            same_teacher_courses=same_teacher_courses)

@course.route('/<int:course_id>/upvote/')
@login_required
def upvote(course_id):
    course = Course.query.get(course_id)
    if not course or course.upvoted:
        return jsonify(ok=False)
    if course.downvoted:
        course.un_downvote()
    ok = course.upvote()
    return jsonify(ok=ok)

@course.route('/<int:course_id>/downvote/')
@login_required
def downvote(course_id):
    course = Course.query.get(course_id)
    if not course or course.downvoted:
        return jsonify(ok=False)
    if course.upvoted:
        course.un_upvote()
    ok = course.downvote()
    return jsonify(ok=ok)


@course.route('/<int:course_id>/reviews/')
def reviews(course_id, course_name=None):
    course = Course.query.get(course_id)
    if not course:
        abort(404)
    #if course_name != course.name:
    #    return redirect(url_for('.review',course_id=course_id,course_name=course.name))

    try:
        page = int(request.args.get('page', 1))
    except:
        page = 1

    reviews = course.reviews.paginate(page=page, per_page=10)
    if reviews.total:
        str = ''
        for item in reviews.items:
            str += item.content + '<a href=' + url_for('review.edit_review', review_id=item.id) +'>Edit</a><br>'
        return str
    else:
        return 'No reviews'




@course.route('/new/',methods=['GET','POST'])
@course.route('/<int:course_id>/edit/',methods=['GET','POSt'])
def edit_course(course_id=None):
    if course_id:
        course = Course.query.get(course_id)
    else:
        course = Course()
    if not course:
        abort(404)
    course_form = CourseForm(request.form, course)
    if course_form.validate_on_submit():
        course_form.populate_obj(course)
        course = course.save()
        flash('course saved')
        return redirect('.view_course', course_id=course.id, course_name=course.name)
    return render_template('edit-course.html', form=course_form)
