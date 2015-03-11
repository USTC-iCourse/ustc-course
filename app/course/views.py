from flask import Blueprint,render_template,abort,redirect,url_for,request

course = Blueprint('course',__name__)

@course.route('/')
def index():
    return 'course'

@course.route('/<int:course_id>/')
def detail(course_id):
    return str(course_id)


@course.route('/new/',methods=['GET','POST'])
@course.route('/<int:course_id>/edit/',methods=['GET','POSt'])
def edit(course_id=None):
    pass
