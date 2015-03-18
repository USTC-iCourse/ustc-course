from flask import Blueprint,render_template,abort,redirect,url_for,request
from app.models import Course

course = Blueprint('course',__name__)

@course.route('/')
def index():
    return render_template('course.html')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    print(page)
    courses_page = Course.query.paginate(page,per_page=20)
    return render_template('course.html',pagination=courses_page)

@course.route('/<int:course_id>/')
def detail(course_id):
    return str(course_id)


@course.route('/new/',methods=['GET','POST'])
@course.route('/<int:course_id>/edit/',methods=['GET','POSt'])
def edit(course_id=None):
    pass
