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

Roles = ['Admin',
        'User']

related_courses = db.Table('related_courses',
    db.Column('src', db.Integer, db.ForeignKey('courses.id'), primary_key=True),
    db.Column('dst', db.Integer, db.ForeignKey('courses.id'), primary_key=True)
)


follow_course = db.Table('follow_course',
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

join_course = db.Table('join_course',
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id'), primary_key=True),
    db.Column('student_id', db.String(20), db.ForeignKey('students.sno'), primary_key=True)
)

upvote_course = db.Table('upvote_course',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id'))
    )

downvote_course = db.Table('downvote_course',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id'))
    )


class User(db.Model, UserMixin):
    __tablename__ = 'users'

    id = db.Column(db.Integer,primary_key=True)
    username = db.Column(db.String(255), unique=True) #用户名
    email = db.Column(db.String(255), unique=True)
    password = db.Column(db.String(255),nullable=False)
    active = db.Column(db.Boolean(), default=True) # 是否已经激活
    role = db.Column(db.String(20),default='User') # 用户或者管理员
    gender = db.Column(db.Enum('male','female','unknown'),default='unknown')
    identity = db.Column(db.Enum('Teacher', 'Student')) # 学生或者教师

    register_time = db.Column(db.DateTime(), default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime())
    last_login_time = db.Column(db.DateTime())#TODO:login

    # We need "use_alter" to avoid circular dependency in FOREIGN KEYs between Student and ImageStore
    homepage = db.Column(db.String(200))  # 用户博客、主页等
    description = db.Column(db.Text)
    _avatar = db.Column(db.String(100))

    courses_following = db.relationship('Course', secondary = follow_course, backref='followers')
    courses_upvoted = db.relationship('Course', secondary = upvote_course, backref='upvote_users')
    courses_downvoted = db.relationship('Course', secondary = downvote_course, backref='downvote_users')
    _student_info = db.relationship('Student', backref='user',uselist=False)
    _teacher_info = db.relationship('Teacher', backref='user',uselist=False)

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.set_password(password)

    def __repr__(self):
        return '<User {} ({})>'.format(self.email, self.password)

    @property
    def reviews_count(self):
        return len(self.reviews)

    @property
    def courses_following_count(self):
        return len(self.courses_following)

    @property
    def courses_upvoted_count(self):
        return len(self.courses_upvoted)

    @property
    def courses_downvoted_count(self):
        return len(self.courses_downvoted)

    @property
    def courses_joined_count(self):
        return len(self.courses_joined)

    @property
    def courses_joined(self):
        if self.is_student and self.info:
            # need .all() because lazy=dynamic
            return self.info.courses_joined.all()
        else:
            return []

    @property
    def avatar(self):
        if self._avatar:
            return '/uploads/images/' + self._avatar
        return '/static/image/user.png'

    def set_avatar(self,avatar):
        self._avatar = avatar

    @property
    def courses_reviewd(self):
        pass

    @property
    def confirmed(self):
        if self.confirmed_at:
            return True
        return False

    @property
    def info(self):
        if self.identity == 'Student':
            return self._student_info
        elif self.identity == 'Teacher':
            return self._teacher_info
        else:
            return None

    def is_student(self):
        return self.identity == 'Student'

    def is_teacher(self):
        return self.identity == 'Teacher'

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
        return user, authenticated, user.confirmed if user else False

    def bind_student(self,sno):
        if self.identity == 'Student':
            student = Student.query.get(sno)
            if student:
                self._student_info = student
                return True,_('Bind student successed!')
            else:
                return False,_('Can\' find a student with ID:%(sno)s!',sno=sno)
        else:
            return False,_('You can\'t bind a student identity.')

    def bind_teacher(self,email):
        if self.identity == 'Teacher':
            teacher = Teacher.query.filter_by(email=email).first()
            if teacher:
                self._teacher_info = teacher
                self.description = teacher.description
                self.homepage = teacher.homepage
                return True,_('Bind student successed!')
            else:
                return False,_('Can\' find a teacher with email:%(email)s!',email=email)
        else:
            return False,_('You can\'t bind a teacher identity.')

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

# 专业
class Major(db.Model):
    __tablename__ = 'majors'

    id = db.Column(db.Integer, unique=True, primary_key=True)
    name = db.Column(db.String(200))
    name_eng = db.Column(db.String(200))
    code = db.Column(db.String(20))

# 行政班级
class DeptClass(db.Model):
    __tablename__ = 'dept_classes'

    id = db.Column(db.Integer, unique=True, primary_key=True)
    name = db.Column(db.String(100))
    dept = db.Column(db.Integer, db.ForeignKey('depts.id'))

# Students could login
class Student(db.Model):
    __tablename__ = 'students'

    sno = db.Column(db.String(20), unique=True, primary_key=True)
    name = db.Column(db.String(80))
    dept_id = db.Column(db.Integer, db.ForeignKey('depts.id'))
    dept_class_id = db.Column(db.Integer, db.ForeignKey('dept_classes.id'))
    major_id = db.Column(db.Integer, db.ForeignKey('majors.id'))
    gender = db.Column(db.Enum('male','female','unknown'),default='unknown')

    user_id = db.Column(db.Integer,db.ForeignKey('users.id'))

    dept = db.relationship('Dept', backref='students')
    dept_class = db.relationship('DeptClass', backref='students')
    major = db.relationship('Major')
    courses_joined = db.relationship('Course', secondary = join_course, backref='students',lazy='dynamic')

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
    title = db.Column(db.String(80))
    office_phone = db.Column(db.String(80))
    gender = db.Column(db.Enum('male','female','unknown'),default='unknown')
    description = db.Column(db.Text())
    homepage = db.Column(db.Text)
    _image = db.Column(db.String(100))

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

    @property
    def image(self):
        if self._image:
            return '/uploads/images/' + self._image
        return '/static/image/user.png'



