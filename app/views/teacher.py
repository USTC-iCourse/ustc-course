from flask import Blueprint,render_template,abort,redirect,url_for,request, abort, flash
from app.models import *
from app.forms import TeacherProfileForm
from flask_login import login_user, current_user, login_required
from app.utils import handle_upload, sanitize
from flask_babel import gettext as _
from .course import QUERY_ORDER
import re

teacher = Blueprint('teacher', __name__)

@teacher.route('/<int:teacher_id>')
@teacher.route('/<int:teacher_id>/')
def view_profile(teacher_id):
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        abort(404)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    courses = teacher.courses.join(CourseRate).order_by(*QUERY_ORDER)
    courses_paged = courses.paginate(page=page, per_page=per_page)
    return render_template('teacher-profile.html', teacher=teacher, courses=courses_paged)

@teacher.route('/<int:teacher_id>/edit_profile/', methods=['GET','POST'])
@login_required
def edit_profile(teacher_id):
    if not current_user.is_admin:
       abort(403)
    teacher = Teacher.query.get(teacher_id)
    form = TeacherProfileForm(formdata=request.form, obj=teacher)
    errors = []
    if form.validate_on_submit():
        #teacher.gender = form['gender'].data
        form['homepage'].data = form['homepage'].data.strip()
        if not form['homepage'].data.startswith('http'):
            form['homepage'].data = 'http://' + form['homepage'].data
        teacher.homepage = form['homepage'].data.strip()
        teacher.description = form['description'].data.strip()
        teacher.research_interest = form['research_interest'].data.strip()
        if request.files.get('avatar'):
            avatar = request.files['avatar']
            ok,info = handle_upload(avatar,'image')
            if ok:
                teacher.set_image(info)
            else:
                errors.append(_("Avatar upload failed"))
        teacher.save()
        db.session.commit()
        return redirect(url_for('teacher.view_profile', teacher_id=teacher.id))
    return render_template('teacher-settings.html', teacher=teacher, errors=errors, form=form)


