from flask import Blueprint,render_template,abort,redirect,url_for,request, abort
from app.models import *
from app.forms import LoginForm, ProfileForm
from flask.ext.login import login_user, current_user, login_required
from app.utils import handle_upload


user = Blueprint('user', __name__)

@user.route('/<int:user_id>')
def view_profile(user_id):
    '''用户的个人主页,展示用户在站点的活跃情况'''
    user = User.query.get(user_id)
    if not user:
        message = '找不到该用户'
        return render_template('feedback.html',status=False,message=message)

    courses_following = user.courses_following
    info = user.info # 注意，教师和学生返回的info类型不同,如果没有验证身份，则返回None
    return render_template('profile.html', user=user)

@user.route('/settings/',methods=['GET','POST'])
@login_required
def account_settings():
    '''账户设置,包括改密码等'''
    user = current_user
    form = ProfileForm(request.form,user)
    errors = []
    if form.validate_on_submit():
        user.username = form['username'].data
        user.homepage = form['homepage'].data
        user.description = form['description'].data
        if request.files.get('avatar'):
            avatar = request.files['avatar']
            ok,info = handle_upload(avatar,'image')
            if ok:
                user.set_avatar(info)
            else:
                errors.append("Avatar upload failed")
        user.save()
    return render_template('settings.html', user=user, errors=errors, form=form)

@user.route('/settings/password',methods=['GET','POST'])
@login_required
def password():
    pass

@user.route('/<int:user_id>/avatar')
def avatar(user_id):
    user = User.query.get(user_id)
    return '<img src='+user.avatar+'>'
