#!/usr/bin/env python3
from flask import Flask, Markup
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKeyConstraint
from datetime import datetime
from app import db, login_manager as lm
from random import randint
from flask_login import UserMixin, current_user
from werkzeug.security import generate_password_hash, \
  check_password_hash
from flask_babel import gettext as _


class Notification(db.Model):
  __tablename__ = 'notifications'

  id = db.Column(db.Integer, primary_key=True)
  to_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
  from_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
  date = db.Column(db.DateTime, default=datetime.utcnow().date())
  time = db.Column(db.DateTime, default=datetime.utcnow())
  operation = db.Column(db.String(50), nullable=False)
  ref_class = db.Column(db.String(50))
  ref_obj_id = db.Column(db.Integer)
  ref_display_class = db.Column(db.String(50))
  display_text = db.Column(db.Text)

  to_user = db.relationship('User', foreign_keys=to_user_id,
                            backref=db.backref('notifications', order_by='desc(Notification.time)'))
  from_user = db.relationship('User', foreign_keys=from_user_id)

  def __init__(self, to_user, from_user, operation, ref_obj, ref_display_class=None, time=None):
    self.to_user = to_user
    self.from_user = from_user
    self.date = time.date() if time else datetime.utcnow().date()
    self.time = time or datetime.utcnow()
    self.operation = operation
    self.ref_class = ref_obj.__class__.__name__
    self.ref_display_class = ref_display_class or self.ref_class
    self.ref_obj_id = ref_obj.id

  def save(self):
    self.display_text = self.__display_text
    db.session.add(self)
    db.session.commit()

  @property
  def ref_obj(self):
    from .review import Review, ReviewComment
    from .course import Course
    from .user import User, Teacher
    if self.ref_class == 'Review':
      return Review.query.get(self.ref_obj_id)
    elif self.ref_class == 'ReviewComment':
      return ReviewComment.query.get(self.ref_obj_id)
    elif self.ref_class == 'Course':
      return Course.query.get(self.ref_obj_id)
    elif self.ref_class == 'User':
      return User.query.get(self.ref_obj_id)
    elif self.ref_class == 'Teacher':
      return Teacher.query.get(self.ref_obj_id)
    else:
      return None

  @property
  def class_name(self):
    class_names = {
      'Review': '点评',
      'ReviewComment': '评论',
      'Course': '课程',
      'User': '用户',
      'Teacher': '老师',
    }
    if self.ref_class in class_names:
      return class_names[self.ref_class]
    else:
      return 'doge'

  @property
  def ref_obj_name(self):
    if self.ref_display_class == 'Review':
      author_link = self.ref_obj.author.link if not self.ref_obj.is_anonymous else '匿名用户'
      return '课程「' + self.ref_obj.link + '」中 ' + author_link + ' 的点评'
    elif self.ref_display_class == 'ReviewComment':
      review_author_link = self.ref_obj.review.author.link if not self.ref_obj.review.is_anonymous else '匿名用户'
      return '课程「' + self.ref_obj.review.link + '」中 ' + review_author_link + ' 的点评中 ' + self.ref_obj.author.link + ' 的评论'
    elif self.ref_display_class == 'Course':
      return '课程「' + self.ref_obj.link + '」'
    elif self.ref_display_class == 'User':
      if self.ref_obj == current_user:
        return '你'
      else:
        return '用户「' + self.ref_obj.link + '」'
    elif self.ref_display_class == 'Teacher':
      return '老师「' + self.ref_obj.link + '」'
    else:
      return 'doge'

  @property
  def community_rules_link(self):
    return Markup('<a href="/community-rules/">') + Markup.escape('社区规范') + Markup('</a>')

  @property
  def operation_text(self):
    if self.operation == 'mention':
      return '在' + self.ref_obj_name + '中提到了你'
    elif self.operation == 'upvote':
      return '给' + self.ref_obj_name + '点了个赞'
    elif self.operation == 'downvote':
      return '给' + self.ref_obj_name + '点了不推荐'
    elif self.operation == 'comment':
      return '评论了' + self.ref_obj_name
    elif self.operation == 'review':
      return '点评了' + self.ref_obj_name
    elif self.operation == 'update-review':
      return '更新了点评' + self.ref_obj_name
    elif self.operation == 'follow':
      return '关注了' + self.ref_obj_name
    elif self.operation == 'block-review':
      return '您在课程「' + self.ref_obj.link + '」中的点评因违反' + self.community_rules_link + '，已被屏蔽'
    elif self.operation == 'unblock-review':
      return '您在课程「' + self.ref_obj.link + '」中的点评已被解除屏蔽'
    else:
      return 'doge'

  @property
  def __display_text(self):
    try:
      if self.operation in ['block-review', 'unblock-review']:
        return self.operation_text
      elif self.ref_class == 'Review' and self.ref_obj.is_anonymous and self.operation != 'comment':
        return '匿名用户 ' + self.operation_text
      else:
        return self.from_user.link + ' ' + self.operation_text
    except:
      return ""

  @property
  def url(self):
    return self.ref_obj.url

  @property
  def link(self):
    return self.ref_obj.link

  @staticmethod
  def remove(from_user, to_user, operation):
    Notification.query.filter_by(from_user_id=from_user.id, to_user_id=to_user.id, operation='upvote').delete()
    db.session.commit()
