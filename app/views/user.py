from flask import Blueprint,render_template,abort,redirect,url_for,request, abort
from app.models import *
from app.forms import LoginForm
from flask.ext.login import login_user, current_user


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

@user.route('/<int:user_id>/settings/')
def account_settings(user_id):
    '''账户设置,包括改密码等'''
    user = User.query.get(user_id)
    if current_user.id != user_id:
        message = '你没有权限访问此页面'
        return render_template('feedback.html',status=False,message=message)

    return render_template('settings.html', user=user)


