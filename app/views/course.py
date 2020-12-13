from flask import Blueprint,render_template,abort,redirect,url_for,request,abort,jsonify
from flask_login import login_required
from flask_babel import gettext as _
from app.models import *
from app.forms import ReviewForm, CourseForm
from app import db
from app.utils import sanitize

course = Blueprint('course',__name__)

deptlist = [
    [27, '体育'],
    [73, '外语'],
    [70, '数院'],
    [40, '信院'],
    [34, '物院'],
    [20, '化院'],
    [38, '地空'],
    [37, '生院'],
    [72, '精仪'],
    [18, '统计'],
    [74, '计院'],
    [30, '人文'],
    [4, '近代物理'],
    [24, '电子'],
    [31, '马克思'],
    [53, '教务处'],
    [71, '近代力学'],
    [7, '电子工程'],
    [13, '化学物理'],
    [11, '自动化'],
    [26, '科技传播'],
    [23, '天文'],
]

@course.route('/')
def index():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    course_type = request.args.get('type',None,type=int)
    department = request.args.get('dept',None,type=int)
    campus = request.args.get('campus',None,type=str)
    course_query = Course.query
    #if course_type:
    #    # 课程类型
    #    course_query = course_query.filter(Course.course_type==course_type)
    #if department:
    #    # 开课院系
    #    course_query = course_query.filter(Course.dept_id==department)
    #if campus:
    #    # 开课地点
    #    course_query = course_query.filter(Course.campus==campus)

    courses_page = course_query.join(CourseRate).order_by(Course.QUERY_ORDER()).paginate(page,per_page=per_page)
    return render_template('course-index.html', courses=courses_page,
            dept=department, deptlist=deptlist, title='好评课程',
            this_module='course.index')

@course.route('/popular/')
def popular():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    course_type = request.args.get('type',None,type=int)
    department = request.args.get('dept',None,type=int)
    campus = request.args.get('campus',None,type=str)
    course_query = Course.query
    #if course_type:
    #    # 课程类型
    #    course_query = course_query.filter(Course.course_type==course_type)
    #if department:
    #    # 开课院系
    #    course_query = course_query.filter(Course.dept_id==department)
    #if campus:
    #    # 开课地点
    #    course_query = course_query.filter(Course.campus==campus)

    courses_page = course_query.join(CourseRate).order_by(CourseRate.review_count.desc(), CourseRate._rate_average.desc()).paginate(page,per_page=per_page)
    return render_template('course-index.html', courses=courses_page,
            dept=department, deptlist=deptlist, title='热门课程',
            this_module='course.popular')

@course.route('/public/')
def public_courses():
    # large enough per_page to disable pagination effectively
    courses_page = Course.query.join(CourseTerm).filter(CourseTerm.join_type == '公选').join(CourseRate).order_by(Course.QUERY_ORDER()).paginate(1, per_page=10000)

    #courses = course_query.join(CourseTerm).filter(CourseTerm.join_type == '公选').join(CourseRate).order_by(Course.QUERY_ORDER()).all()
    #class my_pagination():
    #    def __init__(self, courses):
    #        self.items = courses
    #        self.total = len(courses)
    #        self.page = 1
    #        self.has_prev = False
    #        self.has_next = False
    #    def iter_pages(self, left_edge, right_edge):
    #        return [1]

    #courses_page = my_pagination(courses)
    return render_template('course-index.html', courses=courses_page,
            title='公选课程',
            this_module='course.public_courses')

@course.route('/<int:course_id>/')
def view_course(course_id):
    course = Course.query.get(course_id)
    if not course:
        abort(404)

    related_courses = Course.query.filter_by(name=course.name).all()
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
            same_teacher_courses=same_teacher_courses,
            user=current_user)

@course.route('/<int:course_id>/upvote/', methods=['POST'])
@login_required
def upvote(course_id):
    course = Course.query.get(course_id)
    if not course or course.upvoted:
        return jsonify(ok=False)
    if course.downvoted:
        course.un_downvote()
    ok = course.upvote()
    for user in set(current_user.followers + course.followers):
        user.notify('upvote', course)
    return jsonify(ok=ok, count=course.upvote_count)

@course.route('/<int:course_id>/undo-upvote/', methods=['POST'])
@login_required
def undo_upvote(course_id):
    course = Course.query.get(course_id)
    if not course or not course.upvoted:
        return jsonify(ok=False)
    ok = course.un_upvote()
    return jsonify(ok=ok, count=course.upvote_count)

@course.route('/<int:course_id>/downvote/', methods=['POST'])
@login_required
def downvote(course_id):
    course = Course.query.get(course_id)
    if not course or course.downvoted:
        return jsonify(ok=False)
    if course.upvoted:
        course.un_upvote()
    ok = course.downvote()
    for user in set(current_user.followers + course.followers):
        user.notify('downvote', course)
    return jsonify(ok=ok, count=course.downvote_count)

@course.route('/<int:course_id>/undo-downvote/', methods=['POST'])
@login_required
def undo_downvote(course_id):
    course = Course.query.get(course_id)
    if not course or not course.downvoted:
        return jsonify(ok=False)
    ok = course.un_downvote()
    return jsonify(ok=ok, count=course.downvote_count)

@course.route('/<int:course_id>/follow/', methods=['POST'])
@login_required
def follow(course_id):
    course = Course.query.get(course_id)
    if not course or course.following:
        return jsonify(ok=False)
    ok = course.follow()
    for user in set(current_user.followers + course.followers):
        user.notify('follow', course)
    return jsonify(ok=ok, count=course.follow_count)

@course.route('/<int:course_id>/unfollow/', methods=['POST'])
@login_required
def unfollow(course_id):
    course = Course.query.get(course_id)
    if not course or not course.following:
        return jsonify(ok=False)
    ok = course.unfollow()
    return jsonify(ok=ok, count=course.follow_count)

@course.route('/<int:course_id>/join/', methods=['POST'])
@login_required
def join(course_id):
    course = Course.query.get(course_id)
    if not course or course.joined:
        return jsonify(ok=False)
    ok = course.join()
    return jsonify(ok=ok)

@course.route('/<int:course_id>/quit/',
methods=['POST'])
@login_required
def quit(course_id):
    course = Course.query.get(course_id)
    if not course or not course.joined:
        return jsonify(ok=False)
    ok = course.quit()
    return jsonify(ok=ok)

@course.route('/<int:course_id>/reviews/')
def reviews(course_id):
    course = Course.query.get(course_id)
    if not course:
        abort(404)

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

@course.route('/s/<string:id>/')
def student_courses(id):
    student = Student.query.get(id)
    if student:
        page = request.args.get('page',1,type=int)
        per_page = request.args.get('perpage',15,type=int)
        courses_page = student.courses_joined.join(CourseRate).order_by(Course.QUERY_ORDER()).paginate(page=page,per_page=per_page)
        return render_template('list-courses.html',student=student,courses=courses_page)
    else:
        return render_template('feedback.html',status=False,message=_('We cant\'t find the User!'))

@course.route('/t/<int:id>/')
def teacher_courses(id):
    teacher = Teacher.query.get(id)
    if teacher:
        page = request.args.get('page',1,type=int)
        per_page = request.args.get('perpage',15,type=int)
        courses_page = teacher.courses.join(CourseRate).order_by(Course.QUERY_ORDER()).paginate(page=page,per_page=per_page)
        return render_template('list-courses.html',teacher=teacher,courses=courses_page)
    else:
        return render_template('feedback.html',status=False,message=_('We cant\'t find the User!'))

@course.route('/c/<string:name>/')
def same_name_courses(name):
    name = name.strip()
    page = request.args.get('page',1,type=int)
    per_page = request.args.get('perpage',15,type=int)
    courses_page = Course.query.filter_by(name=name).join(CourseRate).order_by(Course.QUERY_ORDER()).paginate(page=page,per_page=per_page)
    if courses_page.items:
        return render_template('list-courses.html',course_name=name,courses=courses_page)
    else:
        return render_template('list-courses.html',course_name=name,courses=courses_page,message=_("No course called %(name)s found!",name=name))

@course.route('/goto/<string:cno>')
def course_redirect_cno(cno):
    cno = cno.strip()
    course_class = CourseClass.query.filter_by(cno=cno).order_by(CourseClass.term.desc()).all()
    if len(course_class) > 0:
        return redirect(url_for('course.view_course', course_id=course_class[0].course_id))
    else:
        abort(404)

@course.route('/goto/<string:cno>/<int:term>')
def course_redirect_cno_term(cno, term):
    cno = cno.strip()
    term = int(term)
    course_class = CourseClass.query.filter_by(cno=cno, term=term).all()
    if len(course_class) > 0:
        return redirect(url_for('course.view_course', course_id=course_class[0].course_id))
    else:
        abort(404)



@course.route('/<int:course_id>/profile_history/', methods=['GET'])
@login_required
def profile_history(course_id):
    course = Course.query.get(course_id)
    if not course:
        abort(404)
    return render_template('course-profile-history.html', course=course)


@course.route('/new/',methods=['GET','POST'])
@course.route('/<int:course_id>/edit/',methods=['GET','POST'])
@login_required
def edit_course(course_id=None):
    if course_id:
        course = Course.query.get(course_id)
    else:
        course = Course()
    if not course:
        abort(404)
    course_form = CourseForm(formdata=request.form, obj=course)
    if course_form.validate_on_submit():
        course_form.introduction.data = sanitize(course_form.introduction.data)
        course_form.populate_obj(course)
        if not course.homepage.startswith('http'):
            course.homepage = 'http://' + course.homepage
        course.save()

        info_history = CourseInfoHistory()
        info_history.save(course, current_user) 

        db.session.commit()
        return redirect(url_for('course.view_course', course_id=course.id))
    return render_template('course-edit.html', form=course_form, course=course)


@course.route('/<int:course_id>/remove_teacher/', methods=['POST'])
@login_required
def remove_teacher(course_id):
    if not current_user.is_admin:
        abort(403)
    teacher_id = request.form.get('teacher_id')
    if not teacher_id:
        return jsonify(ok=False, message=_('Teacher ID Not Specified'))
    course = Course.query.get(course_id)
    if not course:
        return jsonify(ok=False, message=_('Course Not Found'))
    ok = False
    new_teachers = []
    for teacher in course.teachers:
        if str(teacher.id) == teacher_id:
            ok = True
        else:
            new_teachers.append(teacher)

    if not ok:
        return jsonify(ok=False, message=_('Teacher Not Found In Course'))
    course.teachers = new_teachers
    db.session.commit()
    return jsonify(ok=True)


@course.route('/<int:course_id>/add_teacher/', methods=['POST'])
@login_required
def add_teacher(course_id):
    if not current_user.is_admin:
        abort(403)
    teacher_id = request.form.get('teacher_id')
    if not teacher_id:
        return jsonify(ok=False, message=_('Teacher ID Not Specified'))
    course = Course.query.get(course_id)
    if not course:
        return jsonify(ok=False, message=_('Course Not Found'))
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify(ok=False, message=_('Teacher ID Not Found'))
    if teacher in course.teachers:
        return jsonify(ok=False, message=_('Teacher Already Exists In Course'))
    course.teachers.append(teacher)
    db.session.commit()
    return jsonify(ok=True)
