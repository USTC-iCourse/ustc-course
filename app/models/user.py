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

Roles = ['Admin',
        'User']

Identidies =['Teacher',
        'Student']

related_courses = db.Table('related_courses',
    db.Column('src', db.Integer, db.ForeignKey('courses.id'), primary_key=True),
    db.Column('dst', db.Integer, db.ForeignKey('courses.id'), primary_key=True)
)

class FollowCourse(db.Model):
    __tablename__ = 'follow_course'

    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)

    follow_time = db.Column(db.DateTime)

    course = db.relationship('Course')

class JoinCourse(db.Model):
    __tablename__ = 'join_course'

    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), primary_key=True)
    student_id = db.Column(db.String(20), db.ForeignKey('students.sno'), primary_key=True)

    course_type = db.Column(db.String(1))    # 课程类别
    course_attr = db.Column(db.String(1))    # 课程属性
    join_time = db.Column(db.DateTime)  # 选课时间

    course = db.relationship('Course')


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(255), unique=True) #用户名
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255),nullable=False)
    active = db.Column(db.Boolean(), default=True) # 是否已经激活
    role = db.Column(db.String(20),default='User') # 用户或者管理员
    identity = db.Column(db.String(20)) # 学生或者教师
    register_time = db.Column(db.DateTime(), default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime())
    last_login_time = db.Column(db.DateTime())#TODO:login

    # We need "use_alter" to avoid circular dependency in FOREIGN KEYs between Student and ImageStore
    homepage = db.Column(db.String(200))
    description = db.Column(db.Text)
    _avatar = db.Column(db.String(100))

    courses_following = db.relationship('FollowCourse', backref='followers')
    student_info = db.relationship('Student', backref='user',uselist=False)
    teacher_info = db.relationship('Teacher', backref='user',uselist=False)

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.set_password(password)

    def __repr__(self):
        return '<User {} ({})>'.format(self.email, self.password)

    @property
    def avatar(self):
        if self._avatar:
            return '/uploads/images/' + self._avatar
        return '/static/image/user.png'

    def set_avatar(self,avatar):
        self._avatar = avatar

    @property
    def confirmed(self):
        if self.confirmed_at:
            return True
        return False

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

    def confirm(self):
        self.confirmed_at = datetime.utcnow()
        self.save()

    def set_password(self, password):
        self.password = generate_password_hash(password)
        self.save()

    def check_password(self,password):
        """Check passwords.Returns ture if matchs"""
        if self.password is None:
            return False
        return check_password_hash(self.password,password)

    @classmethod
    def authenticate(cls,login,password):
        """A classmethod for authenticating users
        It returns true if the user exists and has entered a correct password
        :param login: This can be either a username or a email address.
        :param password: The password that is connected to username and email.
        """

        user = cls.query.filter(db.or_(User.username == login,
                                       User.email == login)).first()

        if user and user.confirmed:
            authenticated = user.check_password(password)
        else:
            authenticated = False
        return user, authenticated



    def save(self):
        db.session.add(self)
        db.session.commit()

@lm.user_loader
def load_user(userid):
    return User.query.get(userid)


# Department
class Dept(db.Model):
    __tablename__ = 'depts'

    id = db.Column(db.Integer, unique=True, primary_key=True)
    name = db.Column(db.String(100))
    name_eng = db.Column(db.String(200))


# Students could login
class Student(db.Model):
    __tablename__ = 'students'

    sno = db.Column(db.String(20), unique=True, primary_key=True)
    name = db.Column(db.String(80))
    dept_id = db.Column(db.Integer, db.ForeignKey('depts.id'))
    dept_class = db.Column(db.String(80))
    major = db.Column(db.String(80))

    user_id = db.Column(db.Integer,db.ForeignKey('users.id'))

    dept = db.relationship('Dept', backref='students')
    courses_joined = db.relationship('JoinCourse', backref='students')

    def __repr__(self):
        return '<Student {} ({})>'.format(self.name, self.sno)

    @classmethod
    def create(cls, sno, name, dept=None):
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
            student = cls(sno=sno, name=name, dept=dept)
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

    id = db.Column(db.Integer, unique=True, primary_key=True)

    name = db.Column(db.String(80))
    dept_id = db.Column(db.Integer, db.ForeignKey('depts.id'))

    email = db.Column(db.String(80))
    description = db.Column(db.Text())
    homepage = db.Column(db.Text)

    user_id = db.Column(db.Integer,db.ForeignKey('users.id'))

    avatar = db.Column(db.Integer, db.ForeignKey('image_store.id'))
    dept = db.relationship('Dept', backref='teachers')
    #course

    def __repr__(self):
        return '<Teacher {}: {}'.format(self.id, self.name)

    @classmethod
    def create(cls, tno, name, dept=None,email=None,description=None):
        if cls.query.get(tno):
            return None
        else:
            teacher=cls(tno=tno, name=name, dept=dept, email=email, description=description)
            db.session.add(teacher)
            db.session.commit()
            return teacher



