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

related_courses = db.Table('related_course',
    db.Column('src', db.Integer, db.ForeignKey('courses.id'), primary_key=True),
    db.Column('dst', db.Integer, db.ForeignKey('courses.id'), primary_key=True)
)

follow_course = db.Table('follow_course',
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

join_course = db.Table('join_course',
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id'), primary_key=True),
    db.Column('student_id', db.Integer, db.ForeignKey('students.sno'), primary_key=True)
)

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
    last_login_time = db.Column(db.DateTime())
    register_token = db.Column(db.String(40)) # 注册验证 token

    # We need "use_alter" to avoid circular dependency in FOREIGN KEYs between Student and ImageStore
    avatar = db.Column(db.Integer, db.ForeignKey('image_store.id', name='avatar_storage', use_alter=True))

    courses_following = db.relationship('Course',secondary=follow_course, backref='followers')
    student_info = db.relationship('Student', backref='user',uselist=False)
    teacher_info = db.relationship('Teacher', backref='user',uselist=False)

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.set_password(password)

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

    def set_password(self, password):
        self.password = generate_password_hash(password)

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

        if user:
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




# Students could login
class Student(db.Model):
    __tablename__ = 'students'

    sno = db.Column(db.String(20), unique=True, primary_key=True)
    name = db.Column(db.String(80))
    dept = db.Column(db.String(80))
    description = db.Column(db.Text())

    user_id = db.Column(db.Integer,db.ForeignKey('users.id'))

    courses_joined = db.relationship('Course',secondary=join_course, backref='students')

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

    id = db.Column(db.Integer, unique=True, primary_key=True)

    name = db.Column(db.String(80))
    dept = db.Column(db.String(80))

    email = db.Column(db.String(80))
    description = db.Column(db.Text())

    user_id = db.Column(db.Integer,db.ForeignKey('users.id'))

    #course

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



