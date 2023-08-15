from flask import Blueprint, render_template, abort, redirect, url_for, request, abort, flash, make_response
from app.models import *
from app.forms import LoginForm, ProfileForm, PasswordForm
from flask_login import login_user, current_user, login_required
from app.utils import handle_upload, resize_avatar, sanitize, cal_validation_code
from flask_babel import gettext as _
import re

user = Blueprint('user', __name__)


@user.route('/<int:user_id>')
def view_profile(user_id):
  '''用户的个人主页,展示用户在站点的活跃情况'''
  user = User.query.get(user_id)
  if not user or user.is_deleted:
    message = '用户不存在！'
    return render_template('feedback.html', status=False, message=message)
  if user.is_profile_hidden and current_user != user:
    message = '此用户的个人主页未公开！'
    return render_template('feedback.html', status=False, message=message)

  user.access_count += 1
  user.save_without_edit()

  return render_template('profile.html',
                         user=user,
                         info=(user.info if user.is_student else None),
                         current_user=current_user,
                         title=user.username,
                         description=user.username + ' 写了 ' + str(user.reviews_count) + ' 条点评，关注了 ' + str(
                           user.courses_following_count) + ' 门课')


@user.route('/<int:user_id>/reviews')
def reviews(user_id):
  '''用户点评过的所有课程'''
  user = User.query.get(user_id)
  if not user or user.is_deleted:
    message = '用户不存在！'
    return render_template('feedback.html', status=False, message=message)
  if user.is_profile_hidden and current_user != user:
    message = '此用户的个人主页未公开！'
    return render_template('feedback.html', status=False, message=message)

  return render_template('user-reviews.html',
                         user=user,
                         info=(user.info if user.is_student else None),
                         title=user.username + ' 的点评',
                         description=user.username + ' 写了 ' + str(user.reviews_count) + ' 条点评')


@user.route('/<int:user_id>/follow-course')
def follow_course(user_id):
  '''用户关注过的所有课程'''
  user = User.query.get(user_id)
  if not user or user.is_deleted:
    message = '用户不存在！'
    return render_template('feedback.html', status=False, message=message)
  if (user.is_profile_hidden or user.is_following_hidden) and current_user != user:
    message = '此用户关注的课程未公开！'
    return render_template('feedback.html', status=False, message=message)

  return render_template('follow-course.html',
                         user=user,
                         courses=user.courses_following,
                         info=(user.info if user.is_student else None),
                         title=user.username + ' 的关注',
                         description=user.username + ' 关注了 ' + str(user.courses_following_count) + ' 门课程')


@user.route('/<int:user_id>/join-course')
@login_required
def join_course(user_id):
  '''用户学过的所有课程'''
  user = User.query.get(user_id)
  if not user or user.is_deleted:
    message = '用户不存在！'
    return render_template('feedback.html', status=False, message=message)
  if (user.is_profile_hidden or user.is_following_hidden) and current_user != user:
    message = '此用户学过的课程未公开！'
    return render_template('feedback.html', status=False, message=message)

  return render_template('join-course.html',
                         user=user,
                         courses=user.courses_joined,
                         info=(user.info if user.is_student else None),
                         title=user.username + ' 学过的课程',
                         description=user.username + ' 学过 ' + str(len(user.courses_joined)) + ' 门课')


@user.route('/settings/', methods=['GET', 'POST'])
@login_required
def account_settings():
  '''账户设置,包括改密码等'''
  user = current_user
  form = ProfileForm(formdata=request.form, obj=user)
  errors = []
  if form.validate_on_submit():
    username = form['username'].data.strip()
    if username == user.username:
      pass
    elif User.query.filter_by(username=username).all():
      errors.append(_("Sorry, the username " + username + " has been taken!"))
    else:
      user.username = username

    user.homepage = form['homepage'].data.strip()
    if not user.homepage.startswith('http'):
      user.homepage = 'http://' + user.homepage
    user.description = form['description'].data.strip()
    if request.files.get('avatar'):
      avatar = request.files['avatar']
      ok, info = handle_upload(avatar, 'image')
      if ok:
        user.set_avatar(resize_avatar(info))
      else:
        errors.append(_("Avatar upload failed"))

    user.is_following_hidden = form['is_following_hidden'].data
    user.is_profile_hidden = form['is_profile_hidden'].data

    user.save()
  elif request.method == 'POST':
    errors = ['表单验证错误：' + str(form.errors)]
  return render_template('settings.html', user=user, form=form, errors=errors, title='用户设置')


@user.route('/settings/bind/', methods=['GET', 'POST'])
@login_required
def bind_identity():
  user = current_user
  identity = current_user.identity
  form = ProfileForm(formdata=request.form, obj=user)
  if identity == 'Student':
    if request.method == "POST":
      sno = request.form.get('sno')
      if sno:
        ok, message = current_user.bind_student(sno)
        current_user.save()
        if ok:
          return redirect(url_for('.account_settings'))
        else:
          return render_template('bind-stu.html', user=current_user, error=message)
      else:
        error = _('必须输入一个学号!')
        return render_template('bind-stu.html', user=current_user, error=error, title='绑定学号')
    else:
      return render_template('bind-stu.html', user=current_user, error=None, title='绑定学号')
  elif identity == 'Teacher':
    return render_template('feedback.html', status=False, message=_('教师不能绑定学号！'), title='绑定学号')
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
      return render_template('feedback.html', status=False, message=_('The server met some problem.Please contact us.'))


@user.route('/<int:user_id>/courses/')
def courses(user_id):
  user = User.query.get(user_id)
  if user and user.info:
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('perpage', 15, type=int)
    if user.is_teacher:
      courses_page = user.info.courses.paginate(page=page, per_page=per_page)
      return render_template('list-courses.html', teacher=user.info, courses=courses_page)
    elif user.is_student:
      courses_page = user.info.courses_joined.paginate(page=page, per_page=per_page)
      return render_template('list-courses.html', student=user.info, courses=courses_page)
    else:
      return render_template('feedback.html', status=False, message=_('Error: please contact us!'))
  elif user and not user.is_deleted:
    return render_template('feedback.html', status=False, message=_('此用户尚未绑定学号。\
            <a href=%(url)s><b>点击这里</b></a> 绑定学号。', url=url_for('.bind_identity')))
  else:
    return render_template('feedback.html', status=False, message=_('We can\'t find the User!'))


@user.route('/<int:user_id>/avatar')
def avatar(user_id):
  user = User.query.get(user_id)
  return '<img src=' + user.avatar + '>'


@user.route('/notifications/')
@login_required
def notice():
  # accessing notice page clears unread notifications
  current_user.unread_notification_count = 0
  current_user.save()
  rss_url = url_for('user.notice_rss', user_id=current_user.id, validation_code=cal_validation_code(current_user))
  return render_template('notice.html', rss_url=rss_url, notifications=current_user.notifications, title='通知消息')


@user.route('/<int:user_id>/followers')
def followers(user_id):
  '''被关注的人页面'''
  user = User.query.get(user_id)
  if not user or user.is_deleted:
    message = '用户不存在！'
    return render_template('feedback.html', status=False, message=message)
  if (user.is_profile_hidden or user.is_following_hidden) and current_user != user:
    message = '此用户的粉丝列表未公开！'
    return render_template('feedback.html', status=False, message=message)

  return render_template('followers.html',
                         user=user, title=user.username + ' 被关注',
                         description=user.username + ' 被 ' + str(user.follower_count) + ' 人关注')


@user.route('/<int:user_id>/followings')
def followings(user_id):
  '''关注的人页面'''
  user = User.query.get(user_id)
  if not user or user.is_deleted:
    message = '用户不存在！'
    return render_template('feedback.html', status=False, message=message)
  if (user.is_profile_hidden or user.is_following_hidden) and current_user != user:
    message = '此用户关注的人未公开！'
    return render_template('feedback.html', status=False, message=message)

  return render_template('followings.html',
                         user=user, title=user.username + ' 关注的人',
                         description=user.username + ' 关注了 ' + str(user.following_count) + ' 人')


@user.route('/<int:user_id>/feed/<string:validation_code>')
def notice_rss(user_id, validation_code):
  user = User.query.get(user_id)
  if not user or user.is_deleted:
    abort(404)
  expected = cal_validation_code(user)
  if expected != validation_code:
    abort(403)
  rss_content = render_template('notice.xml', notifications=user.notifications)
  response = make_response(rss_content)
  response.headers['Content-Type'] = 'application/rss+xml'
  return response
