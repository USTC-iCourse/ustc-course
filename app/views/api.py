from flask import Blueprint, jsonify, request, Markup, redirect, render_template, abort
from flask_login import login_required, current_user
from app.models import Review, ReviewComment, User, Course, ImageStore, Notification
from app.models import ReviewCommentHistory, ThirdPartySigninHistory
from app.forms import ReviewCommentForm
from app.utils import rand_str, handle_upload, validate_username, validate_email
from app.utils import editor_parse_at
from app.views.review import record_review_history
from flask_babel import gettext as _
from app import app
import hashlib
import urllib
import re
import os
from datetime import datetime

api = Blueprint('api', __name__)


@api.route('/review/upvote/', methods=['POST'])
@login_required
def review_upvote():
  review_id = request.values.get('review_id')
  if review_id:
    review = Review.query.with_for_update().get(review_id)
    if review:
      ok, message = review.upvote()
      if ok and current_user != review.author:
        review.author.notify('upvote', review)
      return jsonify(ok=ok, message=message, count=review.upvote_count)
    else:
      return jsonify(ok=False, message="The review doesn't exist.")
  else:
    return jsonify(ok=false, message="A id must be given")


@api.route('/review/cancel_upvote/', methods=['POST'])
@login_required
def review_cancel_upvote():
  review_id = request.values.get('review_id')
  if review_id:
    review = Review.query.with_for_update().get(review_id)
    if review:
      ok, message = review.cancel_upvote()
      if ok:
        Notification.remove(current_user, review.author, 'upvote')
      return jsonify(ok=ok, message=message, count=review.upvote_count)
    else:
      return jsonify(ok=False, message="The review doesn't exist.")
  else:
    return jsonify(ok=False, message="A id must be given")


def record_review_comment_history(comment, operation, commit=True):
  history = ReviewCommentHistory()
  history.review_id = comment.review_id
  history.author_id = comment.author_id
  history.content = comment.content

  history.comment_id = comment.id
  history.operation = operation
  if current_user and current_user.is_authenticated:
    history.operation_user_id = current_user.id

  if commit:
    history.add()
  return history


@api.route('/review/new_comment/', methods=['POST'])
@login_required
def review_new_comment():
  form = ReviewCommentForm(formdata=request.form)
  if form.validate_on_submit():
    review_id = request.form.get('review_id')
    if review_id:
      review = Review.query.with_for_update().get(review_id)
      comment = ReviewComment()
      content = request.form.get('content')
      if len(content) > 500:
        return jsonify(ok=False, message="评论太长了，不能超过 500 字哦")
      content = Markup.escape(content)
      content, mentioned_users = editor_parse_at(content)
      ok, message = comment.add(review, content)
      if ok:
        record_review_comment_history(comment, 'create')
        if review.author != current_user:
          review.author.notify('comment', review)
        for user in mentioned_users:
          user.notify('mention', comment)
      return jsonify(ok=ok, message=message, content=content)
    else:
      return jsonify(ok=False, message="The review doesn't exist.")
  else:
    return jsonify(ok=False, message=('表单验证出错：' + str(form.errors)))


@api.route('/review/delete_comment/', methods=['POST'])
@login_required
def delete_comment():
  comment_id = request.values.get('comment_id')
  if comment_id:
    comment = ReviewComment.query.with_for_update().get(comment_id)
    if comment:
      if comment.author == current_user or current_user.is_admin:
        record_review_comment_history(comment, 'delete')
        ok, message = comment.delete()
        return jsonify(ok=ok, message=message)
      else:
        return jsonify(ok=False, message="Forbidden")
    else:
      return jsonify(ok=False, message="The comment doesn't exist.")
  else:
    return jsonify(ok=False, message="A id must be given")


@api.route('/review/block/', methods=['POST'])
@login_required
def block_review():
  review_id = request.values.get('review_id')
  if review_id:
    review = Review.query.with_for_update().get(review_id)
    if review:
      if current_user.is_admin:
        ok, message = review.block()
        if ok:
          review.course.update_rate()
          review.author.notify('block-review', review)
          send_block_review_email(review)
          record_review_history(review, 'block')
        return jsonify(ok=ok, message=message)
      else:
        return jsonify(ok=False, message="Forbidden")
    else:
      return jsonify(ok=False, message="The review doesn't exist.")
  else:
    return jsonify(ok=False, message="A id must be given")


@api.route('/review/unblock/', methods=['POST'])
@login_required
def unblock_review():
  review_id = request.values.get('review_id')
  if review_id:
    review = Review.query.with_for_update().get(review_id)
    if review:
      if current_user.is_admin:
        ok, message = review.unblock()
        if ok:
          review.course.update_rate()
          review.author.notify('unblock-review', review)
          send_unblock_review_email(review)
          record_review_history(review, 'unblock')
        return jsonify(ok=ok, message=message)
      else:
        return jsonify(ok=False, message="Forbidden")
    else:
      return jsonify(ok=False, message="The review doesn't exist.")
  else:
    return jsonify(ok=False, message="A id must be given")


@api.route('/review/hide/', methods=['POST'])
@login_required
def hide_review():
  review_id = request.values.get('review_id')
  if review_id:
    review = Review.query.with_for_update().get(review_id)
    if review:
      if current_user.is_authenticated and current_user == review.author:
        ok, message = review.hide()
        if ok:
          review.course.update_rate()
          record_review_history(review, 'hide')
        return jsonify(ok=ok, message=message)
      else:
        return jsonify(ok=False, message="Forbidden")
    else:
      return jsonify(ok=False, message="The review doesn't exist.")
  else:
    return jsonify(ok=False, message="A id must be given")


@api.route('/review/unhide/', methods=['POST'])
@login_required
def unhide_review():
  review_id = request.values.get('review_id')
  if review_id:
    review = Review.query.with_for_update().get(review_id)
    if review:
      if current_user.is_authenticated and current_user == review.author:
        ok, message = review.unhide()
        if ok:
          review.course.update_rate()
          record_review_history(review, 'unhide')
        return jsonify(ok=ok, message=message)
      else:
        return jsonify(ok=False, message="Forbidden")
    else:
      return jsonify(ok=False, message="The review doesn't exist.")
  else:
    return jsonify(ok=False, message="A id must be given")


@api.route('/user/follow/', methods=['POST'])
@login_required
def follow_user():
  user_id = request.values.get('user_id')
  user = User.query.with_for_update().get(user_id)
  if user:
    if user == current_user:
      return jsonify(ok=False, message='Cannot follow yourself')
    elif user in current_user.users_following:
      return jsonify(ok=False, message='You have already followed the specified user')
    current_user.follow(user)
    user.notify('follow', user)
    return jsonify(ok=True)
  else:
    return jsonify(ok=False, message='User does not exist')


@api.route('/user/unfollow/', methods=['POST'])
@login_required
def unfollow_user():
  user_id = request.values.get('user_id')
  user = User.query.with_for_update().get(user_id)
  if user:
    if user == current_user:
      return jsonify(ok=False, message='Cannot follow yourself')
    elif user not in current_user.users_following:
      return jsonify(ok=False, message='You have not followed the specified user')
    current_user.unfollow(user)
    return jsonify(ok=True)
  else:
    return jsonify(ok=False, message='User does not exist')


def generic_upload(file, type):
  ok, message = handle_upload(file, type)
  script_head = '<script type="text/javascript">window.parent.CKEDITOR.tools.callFunction(2,'
  script_tail = ');</script>'
  if ok:
    url = '/uploads/' + type + 's/' + message
    return script_head + '"' + url + '"' + script_tail
  else:
    return script_head + '""' + ',' + '"' + message + '"' + script_tail


@api.route('/upload/image', methods=['POST'])
@login_required
@app.csrf.exempt
def upload_image():
  return generic_upload(request.files['upload'], 'image')


@api.route('/upload/file', methods=['POST'])
@login_required
@app.csrf.exempt
def upload_file():
  return generic_upload(request.files['upload'], 'file')


@api.route('/reg_verify', methods=['GET'])
def reg_verify():
  name = request.args.get('name')
  value = request.args.get('value')

  if name == 'username':
    return validate_username(value)
  elif name == 'email':
    return validate_email(value)
  return 'Invalid Request', 400


@api.route('/notifications/', methods=['POST'])
@login_required
def read_notifications():
  current_user.unread_notification_count = 0
  current_user.save()
  return jsonify(ok=True)


