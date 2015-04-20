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
        message = _('Sorry. But we can\'t find the user!')
        return render_template('feedback.html',status=False,message=message)

    courses_following = user.courses_following
    info = user.info # 注意，教师和学生返回的info类型不同,如果没有验证身份，则返回None.现在没做，以后做
    if info:
        courses_joined = user.info.courses_joined
    else:
        courses_joined = None
    num_review = request.args.get('num_review',5,type=int)
    reviews = user.reviews[0:num_review]
    return render_template('profile.html',
            user=user,
            info=info,
            reviews = reviews,
            courses_following=courses_following,
            courses_joined=courses_joined)


@user.route('/settings/',methods=['GET','POST'])
@login_required
def account_settings():
    '''账户设置,包括改密码等'''
    user = current_user
    form = ProfileForm(request.form,user)
    errors = []
    if form.validate_on_submit():
        #user.username = form['username'].data
        user.gender = form['gender'].data
        user.homepage = sanitize(form['homepage'].data.strip())
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
    identity = current_user.identity
    if identity == 'Student':
        if request.method == "POST":
            sno = request.form.get('sno')
            if sno:
                ok,message = current_user.bind_student(sno)
                current_user.save()
                if ok:
                    return render_template('feedback.html',status=True,message=message)
                else:
                    return render_template('bind-stu.html',user=current_user,error=message)
            else:
                error = _('You must specify a student ID!')
                return render_template('bind-stu.html',user=current_user,error=error)
        else:
            return render_template('bind-stu.html',user=current_user,error=None)
    elif identity == 'Teacher':
        return render_template('feedback.html',status=False,message=_('You can\'t bind a teacher identity now.Please contact us for more information.'))
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

@user.route('/<int:user_id>/avatar')
def avatar(user_id):
    user = User.query.get(user_id)
    return '<img src='+user.avatar+'>'
