from flask import Blueprint,render_template,abort,redirect,url_for,request, abort
from app.models import *
from app.forms import LoginForm, ProfileForm,PasswordForm
from flask.ext.login import login_user, current_user, login_required
from app.utils import handle_upload, sanitize
from flask.ext.babel import gettext as _
import re


user = Blueprint('user', __name__)

@user.route('/<int:user_id>')
def view_profile(user_id):
    '''用户的个人主页,展示用户在站点的活跃情况'''
    user = User.query.get(user_id)
    if not user:
        message = _('Sorry. But we could not find the user!')
        return render_template('feedback.html', status=False, message=message)

    return render_template('profile.html',
                           user=user,
                           info=(user.info if user.is_student else None))

@user.route('/<int:user_id>/reviews')
def reviews(user_id):
    '''用户点评过的所有课程'''
    user = User.query.get(user_id)
    if not user:
        message = _('Sorry. But we could not find the user!')
        return render_template('feedback.html', status=False, message=message)

    return render_template('user-reviews.html',
                           user=user,
                           info=(user.info if user.is_student else None))


@user.route('/<int:user_id>/follow-course')
def follow_course(user_id):
    '''用户关注过的所有课程'''
    user = User.query.get(user_id)
    if not user:
        message = _('Sorry. But we could not find the user!')
        return render_template('feedback.html', status=False, message=message)

    return render_template('follow-course.html',
                           user=user,
                           courses=user.courses_following,
                           info=(user.info if user.is_student else None))


@user.route('/<int:user_id>/join-course')
def join_course(user_id):
    '''用户学过的所有课程'''
    user = User.query.get(user_id)
    if not user:
        message = _('Sorry. But we could not find the user!')
        return render_template('feedback.html', status=False, message=message)

    return render_template('join-course.html',
                           user=user,
                           courses=user.courses_joined,
                           info=(user.info if user.is_student else None))



@user.route('/settings/',methods=['GET','POST'])
@login_required
def account_settings():
    '''账户设置,包括改密码等'''
    user = current_user
    form = ProfileForm(request.form, user)
    errors = []
    if form.validate_on_submit():
        #user.username = form['username'].data
        #user.gender = form['gender'].data
        user.homepage = form['homepage'].data.strip()
        user.description = form['description'].data.strip()
        if request.files.get('avatar'):
            avatar = request.files['avatar']
            ok,info = handle_upload(avatar,'image')
            if ok:
                user.set_avatar(info)
            else:
                errors.append(_("Avatar upload failed"))
        user.save()
    return render_template('settings.html', user=user, errors=errors, form=form)

@user.route('/settings/password/',methods=['GET','POST'])
@login_required
def password():
    form = PasswordForm(request.form)
    if form.validate_on_submit():
        current_user.set_password(form.password.data)
        return render_template('feedback.html',status=True,message=_('Password changed!'))
    return render_template('signin.html',form=form)

@user.route('/settings/bind/',methods=['GET','POST'])
@login_required
def bind_identity():
    user = current_user
    identity = current_user.identity
    form = ProfileForm(request.form,user)
    if identity == 'Student':
        if request.method == "POST":
            sno = request.form.get('sno')
            if sno:
                ok,message = current_user.bind_student(sno)
                current_user.save()
                if ok:
                    return redirect(url_for('.account_settings'))
                else:
                    return render_template('bind-stu.html',user=current_user,error=message)
            else:
                error = _('必须输入一个学号!')
                return render_template('bind-stu.html',user=current_user,error=error)
        else:
            return render_template('bind-stu.html',user=current_user,error=None)
    elif identity == 'Teacher':
        return render_template('feedback.html',status=False,message=_('暂时还不能用'))
    else:
        email_suffix = current_user.email.split('@')[-1]
        if email_suffix == 'mail.ustc.edu.cn':
            current_user.identity = 'Student'
            current_user.save()
            return redirect(url_for('.bind_identity'))
        elif email_suffix == 'ustc.edu.cn':
            current_user.identity = 'Teacher'
            current_user.save()
            return redirect(url_for('.bind_identity'))
        else:
            return render_template('feedback.html',status=False,message=_('The server met some problem.Please contact us.'))


@user.route('/<int:user_id>/courses/')
def courses(user_id):
    user = User.query.get(user_id)
    if user and user.info:
        page = request.args.get('page',1,type=int)
        per_page = request.args.get('perpage',15,type=int)
        if user.is_teacher():
            courses_page = user.info.courses.paginate(page=page,per_page=per_page)
            return render_template('list-courses.html',teacher=user.info,courses = courses_page)
        elif user.is_student():
            courses_page = user.info.courses_joined.paginate(page=page,per_page=per_page)
            return render_template('list-courses.html',student=user.info,courses=courses_page)
        else:
            return render_template('feedback.html',status=False,message=_('Erorr 203: please contact us!'))
    elif user:
        return render_template('feedback.html',status=False,message=_('This user have not bind a ID.Click\
            <a href=%(url)s><b>here</b></a> to bind.',url=url_for('.bind_identity')))
    else:
        return render_template('feedback.html',status=False,message=_('We cant\'t find the User!'))



@user.route('/<int:user_id>/avatar')
def avatar(user_id):
    user = User.query.get(user_id)
    return '<img src='+user.avatar+'>'


@user.route('/teacher/<int:teacher_id>/', methods=['GET','POST'])
def teacher_settings(teacher_id):
    '''编辑教师信息'''
    teacher = Teacher.query.get(teacher_id)
    form = ProfileForm(request.form, teacher)
    errors = []
    if form.validate_on_submit():
        #teacher.gender = form['gender'].data
        teacher.homepage = form['homepage'].data.strip()
        teacher.description = form['description'].data.strip()
        if request.files.get('avatar'):
            avatar = request.files['avatar']
            ok,info = handle_upload(avatar,'image')
            if ok:
                teacher.set_image(info)
            else:
                errors.append(_("Avatar upload failed"))
        teacher.save()
    return render_template('teacher-settings.html', teacher=teacher, errors=errors, form=form)