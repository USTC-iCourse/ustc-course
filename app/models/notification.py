#!/usr/bin/env python3
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKeyConstraint
from datetime import datetime
from app import db, login_manager as lm
from random import randint
from flask.ext.login import UserMixin
from werkzeug.security import generate_password_hash, \
     check_password_hash
from flask.ext.babel import gettext as _
from .review import *
from .course import *
from .user import *
from .image import *
from .forum import *
from .note import *
from .share import *

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

    to_user = db.relationship('User', foreign_keys=to_user_id, backref=db.backref('notifications', order_by='desc(Notification.time)'))
    from_user = db.relationship('User', foreign_keys=from_user_id)

    def __init__(self, to_user, from_user, operation, ref_obj, ref_class=None):
        self.to_user = to_user
        self.from_user = from_user
        self.date = datetime.utcnow().date()
        self.time = datetime.utcnow()
        self.operation = operation
        self.ref_class = ref_class or ref_obj.__class__.__name__
        self.ref_obj_id = ref_obj.id

    def save(self):
        db.session.add(self)
        db.session.commit()

    @property
    def ref_obj(self):
        if self.ref_class == 'Review':
            return Review.query.get(Review.id == ref_obj_id)
        elif self.ref_class == 'ReviewComment':
            return ReviewComment.query.get(ReviewComment.id == ref_obj_id)
        elif self.ref_class == 'Course':
            return Course.query.get(Course.id == ref_obj_id)
        elif self.ref_class == 'User':
            return User.query.get(User.id == ref_obj_id)
        elif self.ref_class == 'Teacher':
            return Teacher.query.get(Teacher.id == ref_obj_id)
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
        if self.ref_class == 'Review':
            return '课程「' + self.ref_obj.review.link + '」中 ' + self.ref_obj.author.link + ' 的点评'
        elif self.ref_class == 'ReviewComment':
            return '课程「' + self.ref_obj.review.link + '」中 ' + self.ref_obj.review.author.link + ' 的点评的 ' + self.ref_obj.author.link + ' 的评论'
        elif self.ref_class == 'Course':
            return '课程「' + self.ref_obj.link + '」'
        elif self.ref_class == 'User':
            if self.ref_obj == current_user:
                return '你'
            else:
                return '用户「' + self.ref_obj.link + '」'
        elif self.ref_class == 'Teacher':
            return '老师「' + self.ref_obj.link + '」'
        else:
            return 'doge'

    @property
    def operation_text(self):
        if self.operation == 'mention':
            return '在' + self.ref_obj_name + '中提到了你'
        elif self.operation == 'upvote':
            return '给你在' + self.ref_obj_name + '点了个赞'
        elif self.operation == 'downvote':
            return '给你在' + self.ref_obj_name + '点了个反对'
        elif self.operation == 'comment':
            return '评论了' + self.ref_obj_name
        elif self.operation == 'review':
            return '点评了' + self.ref_obj_name
        elif self.operation == 'follow':
            return '关注了' + self.ref_obj_name
        else:
            return 'doge'

    @property
    def display_text(self):
        return self.from_user.link + ' ' + self.operation_text

    @property
    def link(self):
        return self.ref_obj.link
