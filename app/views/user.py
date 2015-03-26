from flask import Blueprint,render_template,abort,redirect,url_for,request
from app.models import User
from app.forms import LoginForm
from flask.ext.login import login_user


user = Blueprint('user', __name__)

@user.route('/<int:user_id>')
def view_profile():
    '''用户的个人主页,展示用户在站点的活跃情况'''

    return render_template('profile.html')

@user.route('/<int:user_id>/settings/')
def account_settings():
    '''账户设置,包括改密码等'''

    return render_template('settings.html')


