from flask import Blueprint,render_template,abort,redirect,url_for,request
from app.models import Course
from app.forms import ReviewForm

course = Blueprint('course',__name__)

@course.route('/')
def index():
    #return render_template('course.html')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    print(page)
    courses_page = Course.query.paginate(page,per_page=20)
    return render_template('course-index.html',pagination=courses_page)

@course.route('/<int:course_id>/')
@course.route('/<int:course_id>/<course_name>/')
def course_detail(course_id,course_name=None):
    course = Course.query.get(course_id)
    if not course:
        return 404
    if course_name != course.name:
        return redirect(url_for('.course_detail',course_id=course_id,course_name=course.name))

    reviews = course.reviews
    return course_name + str(reviews)
    return str(course_id)

@course.route('/<int:course_id>/<course_name>/review/')
def review(course_id,course_name=None):
    course = Course.query.get(course_id)
    if not course:
        return 404
    if course_name != course.name:
        return redirect(url_for('.review',course_id=course_id,course_name=course.name))

    reviews = course.reviews.pagination(page=1,perpage=10)
    return course_name + str(reviews)
    return str(course_id)



@course.route('/new/',methods=['GET','POST'])
@course.route('/<int:course_id>/edit/',methods=['GET','POSt'])
def edit(course_id=None):
    pass
