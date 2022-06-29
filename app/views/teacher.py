from flask import Blueprint,render_template,abort,redirect,url_for,request, abort, flash
from app.models import *
from app.forms import TeacherProfileForm
from flask_login import login_user, current_user, login_required
from app.utils import handle_upload, sanitize
from flask_babel import gettext as _
import re

teacher = Blueprint('teacher', __name__)

def to_int(data):
    if data is None:
        return 0
    else:
        return int(data)

@teacher.route('/<int:teacher_id>')
@teacher.route('/<int:teacher_id>/')
def view_profile(teacher_id):
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        abort(404)
    teacher.access_count += 1
    teacher.save_without_edit()

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10000, type=int)
    courses = teacher.courses.join(CourseRate).order_by(Course.QUERY_ORDER())
    courses_paged = courses.paginate(page=page, per_page=per_page)

    all_courses = courses.all()
    total_rating = sum([ to_int(course.course_rate._rate_total) for course in all_courses ])
    stats = {}
    stats['num_rating'] = sum([ to_int(course.course_rate.review_count) for course in all_courses ])
    if stats['num_rating'] == 0:
        stats['avg_rating'] = 0
    else:
        stats['avg_rating'] = total_rating * 1.0 / stats['num_rating']
    if len(all_courses) == 0:
        stats['normalized_rating'] = 0
    else:
        stats['normalized_rating'] = all_courses[0].compute_normalized_rate(total_rating, stats['num_rating'])

    return render_template('teacher-profile.html', teacher=teacher, courses=courses_paged, title=teacher.name, stats=stats,
                           description=teacher.name + '共有 ' + str(courses_paged.total) + ' 门课程，' + str(stats['num_rating']) + ' 个点评，平均分 ' + ('%.2f' % stats['avg_rating']))

@teacher.route('/<int:teacher_id>/profile_history/', methods=['GET'])
@login_required
def profile_history(teacher_id):
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        abort(404)
    if not current_user.is_admin and teacher.info_locked:
        abort(403)
    return render_template('teacher-profile-history.html', teacher=teacher, title='教师信息编辑历史 - ' + teacher.name)

@teacher.route('/<int:teacher_id>/edit_profile/', methods=['GET','POST'])
@login_required
def edit_profile(teacher_id):
    teacher = Teacher.query.get(teacher_id)
    form = TeacherProfileForm(formdata=request.form, obj=teacher)
    errors = []
    if teacher.info_locked:
        errors.append(_("Teacher info is locked, please contact administrator to unlock"))
    elif form.validate_on_submit():
        #teacher.gender = form['gender'].data
        form['homepage'].data = form['homepage'].data.strip()
        if not form['homepage'].data.startswith('http'):
            form['homepage'].data = 'http://' + form['homepage'].data
        teacher.homepage = form['homepage'].data.strip()
        teacher.research_interest = form['research_interest'].data.strip()
        if request.files.get('avatar'):
            if teacher.image_locked:
                errors.append(_("Teacher photo is locked, please contact administrator to unlock"))
            else:
                avatar = request.files['avatar']
                ok,info = handle_upload(avatar,'image')
                if ok:
                    teacher.set_image(info)
                else:
                    errors.append(_("Avatar upload failed"))
        teacher.save()

        info_history = TeacherInfoHistory()
        info_history.save(teacher, current_user) 

        return redirect(url_for('teacher.view_profile', teacher_id=teacher.id))
    return render_template('teacher-settings.html', teacher=teacher, errors=errors, form=form, title='编辑教师信息 - ' + teacher.name)

def save_teacher_and_render_template(teacher):
    teacher.save()
    form = TeacherProfileForm(formdata=request.form, obj=teacher)
    errors = []
    return render_template('teacher-settings.html', teacher=teacher, errors=errors, form=form, title='编辑教师信息 - ' + teacher.name)

@teacher.route('/<int:teacher_id>/lock_profile/', methods=['GET','POST'])
@login_required
def lock_profile(teacher_id):
    if not current_user.is_admin:
        abort(403)
    teacher = Teacher.query.get(teacher_id)
    teacher.info_locked = True
    return save_teacher_and_render_template(teacher)

@teacher.route('/<int:teacher_id>/unlock_profile/', methods=['GET','POST'])
@login_required
def unlock_profile(teacher_id):
    if not current_user.is_admin:
        abort(403)
    teacher = Teacher.query.get(teacher_id)
    teacher.info_locked = False
    return save_teacher_and_render_template(teacher)

@teacher.route('/<int:teacher_id>/lock_avatar/', methods=['GET','POST'])
@login_required
def lock_avatar(teacher_id):
    if not current_user.is_admin:
        abort(403)
    teacher = Teacher.query.get(teacher_id)
    teacher.image_locked = True
    return save_teacher_and_render_template(teacher)

@teacher.route('/<int:teacher_id>/unlock_avatar/', methods=['GET','POST'])
@login_required
def unlock_avatar(teacher_id):
    if not current_user.is_admin:
        abort(403)
    teacher = Teacher.query.get(teacher_id)
    teacher.image_locked = False
    return save_teacher_and_render_template(teacher)

