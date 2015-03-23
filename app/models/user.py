#!/usr/bin/env python3
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKeyConstraint
from datetime import datetime
from app import db, login_manager as lm
from random import randint
from flask.ext.login import UserMixin

Roles = ['Admin',
        'User']

Identidies =['Teacher',
        'Student']

related_courses = db.Table('related_course',
    course1 = db.Column(db.Integer, db.ForeignKey('course.id'), primary_key=True),
    course2 = db.Column(db.Integer, db.ForeignKey('course.id'), primary_key=True)
)

follow_course = db.Table('follow_course',
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), primary_key=True),
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
)

join_course = db.Table('join_course',
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.sno'), primary_key=True)
)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer,primary_key=True)
    email = db.Column(db.String(255), unique=True)

    password = db.Column(db.String(80))
    is_admin = db.Column(db.Boolean(), default=False)

    description = db.Column(db.Text())
    register_time = db.Column(db.DateTime(), default=datetime.utcnow)
    last_login_time = db.Column(db.DateTime())

class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer,primary_key=True)
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255),nullable=False)
    nick = db.Column(db.String(120),nullable=False) # 昵称
    active = db.Column(db.Boolean(), default=True) # 是否已经激活
    role = db.Column(db.String(20),default='User') # 用户或者管理员
    identity = db.Column(db.String(20)) # 学生或者教师
    register_time = db.Column(db.DateTime(), default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime())
    last_login_time = db.Column(db.DateTime())
    register_token = db.Column(db.String(40)) # 注册验证 token

    # We need "use_alter" to avoid circular dependency in FOREIGN KEYs between Student and ImageStore
    avatar = db.Column(db.Integer, db.ForeignKey('image_store.id', name='avatar_storage', use_alter=True))

    courses_following = db.relationship('Course',secondary=folowcourse, backref = 'folowers')
    student_info = db.relationship('Student', backref='user',uselist=False)
    teacher_info = db.relationship('Teacher', backref='user',uselist=False)

    def __repr__(self):
        return '<User {} ({})>'.format(self.email, self.password)

    @property
    def info(self):
        if self.identity == 'Student':
            return self.student_info
        elif self.identity == 'Teacher':
            return self.teacher_info
        else:
            return None

    def is_authenticated(self):
        return True

    def is_active(self):
        if self.active:
            return True
        return False


    def save(self):
        db.session.add(self)
        db.session.commit()

@lm.user_loader
def load_user(userid):
    return User.query.get(userid)




# Students could login
class Student(db.Model):
    __tablename__ = 'students'

    sno = db.Column(db.String(20), unique=True, primary_key=True)
    name = db.Column(db.String(80))
    dept = db.Column(db.String(80))
    description = db.Column(db.Text())

    use_id = db.Column(db.Integer,db.ForeignKey('users.id'))

    courses_joined = db.relationship('Course', secondary=joincourse, backref='students')

    def __repr__(self):
        return '<Student {} ({})>'.format(self.name, self.sno)

    @classmethod
    def create(cls, sno, name, dept=None, description=None):
        '''
        creat a Student object and add it to database
        if the student object already exists in the db, it will
            return None.
        :param sno: the student id number
        :param name: the student's name
        :param dept: the department the sutdent belongs to
        :param description:
        '''
        if cls.query.get(sno):
            return None
        else:
            student = cls(sno=sno, name=name, dept=dept, description=description)
            db.session.add(student)
            db.session.commit()
            return student


    # course_type: 计划必修，自由选修……
    def join_course(self, course):
        if not course:
            return None
        self.courses_joined.append(course)
        db.session.add(self)
        db.session.commit()
        return self

    #deprecated
    def follow_course(self, course):
        if not course:
            return None
        self.courses_following.append(course)
        db.session.add(self)
        db.session.commit()
        return self

class Teacher(db.Model):
    __tablename__ = 'teachers'

    tno = db.Column(db.String(20), unique=True, primary_key=True)
    name = db.Column(db.String(80))
    dept = db.Column(db.String(80))

    email = db.Column(db.String(80))
    description = db.Column(db.Text())

    user_id = db.Column(db.Integer,db.ForeignKey('users.id'))

    courses = db.relationship('Course',backref='teacher')


    def __repr__(self):
        return '<Teacher {} ({})'.format(self.name, self.tno)

    @classmethod
    def create(cls, tno, name, dept=None,email=None,description=None):
        if cls.query.get(tno):
            return None
        else:
            teacher=cls(tno=tno, name=name, dept=dept, email=email, description=description)
            db.session.add(teacher)
            db.session.commit()
            return teacher



