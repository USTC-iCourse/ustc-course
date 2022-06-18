#!/usr/bin/env python3
from flask import Flask, url_for, Markup
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKeyConstraint
from datetime import datetime
from app import db, login_manager as lm
from random import randint
from flask_login import UserMixin, current_user
from werkzeug.security import generate_password_hash, \
     check_password_hash
from flask_babel import gettext as _
from .notification import Notification
from werkzeug.contrib.cache import SimpleCache

Roles = ['Admin',
        'User']

follow_course = db.Table('follow_course',
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id'), primary_key=True),
    db.Column('user_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

join_course = db.Table('join_course',
    db.Column('class_id', db.Integer, db.ForeignKey('course_classes.id'), primary_key=True),
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

review_course = db.Table('review_course',
    db.Column('user_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id'))
    )

follow_user = db.Table('follow_user',
    db.Column('follower_id', db.Integer, db.ForeignKey('users.id')),
    db.Column('followed_id', db.Integer, db.ForeignKey('users.id'))
    )

latest_notifications_cache = SimpleCache()

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
    last_edit_time = db.Column(db.DateTime())
    unread_notification_count = db.Column(db.Integer, default=0)

    homepage = db.Column(db.String(200))  # 用户博客、主页等
    description = db.Column(db.Text)
    _avatar = db.Column(db.String(100))
    
    following_count = db.Column(db.Integer, default=0)
    follower_count = db.Column(db.Integer, default=0)
    access_count = db.Column(db.Integer, default=0)

    token_3rdparty = db.Column(db.String(255), nullable=True)

    courses_following = db.relationship('Course', secondary = follow_course, backref='followers')
    courses_upvoted = db.relationship('Course', secondary = upvote_course, backref='upvote_users')
    courses_downvoted = db.relationship('Course', secondary = downvote_course, backref='downvote_users')
    _student_info = db.relationship('Student', backref='user',uselist=False)
    _teacher_info = db.relationship('Teacher', backref='user',uselist=False)
    reviewed_course = db.relationship('Course',secondary = review_course, backref='review_users')
    users_following = db.relationship('User', 
            secondary=follow_user,
            primaryjoin=(follow_user.c.follower_id == id),
            secondaryjoin=(follow_user.c.followed_id == id),
            backref=db.backref('followers'))
    # followers: backref to User
    # notifications: backref to Notification

    def __init__(self, username, email, password):
        self.username = username
        self.email = email
        self.set_password(password)

    def __repr__(self):
        return '<User {} ({})>'.format(self.email, self.password)

    @property
    def url(self):
        return url_for('user.view_profile', user_id=self.id)

    @property
    def link(self):
        return Markup('<a href="' + self.url + '">') + Markup.escape(self.username) + Markup('</a>')

    @property
    def latest_notifications_text(self):
        text = latest_notifications_cache.get(self.id)
        if text is None:
            text = []
            for notice in self.notifications[0:5]:
                text.append(notice.display_text)
            latest_notifications_cache.set(self.id, text)
        return text

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
            return self.info.courses_joined
        else:
            return []

    @property
    def classes_joined_count(self):
        return len(self.classes_joined)

    @property
    def classes_joined(self):
        if self.is_student and self.info:
            return self.info.classes_joined
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

    @property
    def is_student(self):
        return self.identity == 'Student'

    @property
    def student_id(self):
        if self.is_student and self.info:
            return self.info.sno
        else:
            return None

    @property
    def is_teacher(self):
        return self.identity == 'Teacher'

    @property
    def is_authenticated(self):
        return True

    @property
    def is_admin(self):
        return self.role == 'Admin'

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

        if user:
            authenticated = user.check_password(password)
        else:
            authenticated = False
        return user, authenticated, user.confirmed if user else False

    @classmethod
    def authenticate_email(cls, email, password):
        expanded_email_student = email + '@mail.ustc.edu.cn'
        expanded_email_teacher = email + '@ustc.edu.cn'
        user = cls.query.filter(db.or_(User.email == email,
                                       User.email == expanded_email_student,
                                       User.email == expanded_email_teacher)).first()
        if user:
            authenticated = user.check_password(password)
        else:
            authenticated = False
        return user, authenticated, user.confirmed if user else False

    def bind_student(self,sno):
        if self.identity == 'Student':
            student = Student.query.get(sno)
            if student:
                self._student_info = student
                return True,_('成功绑定！')
            else:
                return False,_('找不到这个学号：%(sno)s！',sno=sno)
        else:
            return False,_('无法绑定学号。')

    def bind_teacher(self,email):
        if self.identity == 'Teacher':
            teacher = Teacher.query.filter_by(email=email).first()
            if teacher:
                self._teacher_info = teacher
                self.description = teacher.description
                self.homepage = teacher.homepage
                return True,_('绑定成功！')
            else:
                return False,_('找不到教师邮箱：%(email)s！',email=email)
        else:
            return False,_('无法绑定教师身份。')

    def save(self):
        self.last_edit_time = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def save_without_edit(self):
        db.session.add(self)
        db.session.commit()

    def notify(self, operation, ref_obj, from_user=current_user, ref_display_class=None):
        notification = Notification(self, from_user, operation, ref_obj, ref_display_class)
        notification.save()
        self.unread_notification_count += 1
        db.session.commit()
        # clear cache
        latest_notifications_cache.set(self.id, None)
        return True

    def follow(self, followed):
        if followed in self.users_following:
            return False
        self.users_following.append(followed)
        self.following_count += 1
        followed.follower_count += 1
        db.session.commit()
        return True

    def unfollow(self, followed):
        if followed not in self.users_following:
            return False
        self.users_following.remove(followed)
        self.following_count -= 1
        followed.follower_count -= 1
        db.session.commit()
        return True

    def followed_by(self, user=current_user):
        return user in self.followers

    def following(self, user=current_user):
        return user in self.users_following


@lm.user_loader
def load_user(userid):
    return User.query.get(userid)


# Department
class Dept(db.Model):
    __tablename__ = 'depts'

    id = db.Column(db.Integer, unique=True, primary_key=True)
    name = db.Column(db.String(100))
    name_eng = db.Column(db.String(200))
    code = db.Column(db.String(10))

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
    email = db.Column(db.String(80))
    dept_id = db.Column(db.Integer, db.ForeignKey('depts.id'))
    dept_class_id = db.Column(db.Integer, db.ForeignKey('dept_classes.id'))
    major_id = db.Column(db.Integer, db.ForeignKey('majors.id'))
    gender = db.Column(db.Enum('male','female','unknown'),default='unknown')

    user_id = db.Column(db.Integer,db.ForeignKey('users.id'))

    dept = db.relationship('Dept', backref='students')
    dept_class = db.relationship('DeptClass', backref='students')
    major = db.relationship('Major')
    classes_joined = db.relationship('CourseClass', secondary = join_course, order_by='desc(CourseClass.term)', backref='students')
    courses_joined = db.relationship('CourseClass', secondary = join_course, order_by='desc(CourseClass.term)', overlaps="classes_joined,students")
    
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


    def join_class(self, course):
        if not course:
            return None
        self.classes_joined.append(course)
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



# teacher information history
class TeacherInfoHistory(db.Model):
    __tablename__ = 'teacher_info_history'

    id = db.Column(db.Integer, unique=True, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'))

    author = db.Column(db.Integer, db.ForeignKey('users.id'))
    update_time = db.Column(db.DateTime)

    _image = db.Column(db.String(100))
    homepage = db.Column(db.Text)
    description = db.Column(db.Text)
    research_interest = db.Column(db.Text)

    author_user = db.relationship('User')

    def save(self, teacher, author=current_user):
        self.teacher = teacher
        self.author = author.id
        self.update_time = datetime.utcnow()
        self._image = teacher._image
        self.homepage = teacher.homepage
        self.description = teacher.description
        self.research_interest = teacher.research_interest

        db.session.add(self)
        db.session.commit()

    @property
    def image(self):
        if self._image:
            return '/uploads/images/' + self._image
        return '/static/image/teacher.jpg'


class Teacher(db.Model):
    __tablename__ = 'teachers'

    id = db.Column(db.Integer, unique=True, primary_key=True)

    name = db.Column(db.String(80))
    dept_id = db.Column(db.Integer, db.ForeignKey('depts.id'))

    email = db.Column(db.String(80))
    title = db.Column(db.String(80))
    office_phone = db.Column(db.String(80))
    gender = db.Column(db.Enum('male','female','unknown'),default='unknown')
    description = db.Column(db.Text)
    homepage = db.Column(db.Text)
    research_interest = db.Column(db.Text)
    _image = db.Column(db.String(100))
    last_edit_time = db.Column(db.DateTime)
    image_locked = db.Column(db.Boolean, default=False, nullable=False)
    info_locked = db.Column(db.Boolean, default=False, nullable=False)

    user_id = db.Column(db.Integer,db.ForeignKey('users.id'))

    access_count = db.Column(db.Integer, default=0)

    dept = db.relationship('Dept', backref='teachers')
    #courses: backref to Course

    _info_history = db.relationship('TeacherInfoHistory', order_by='desc(TeacherInfoHistory.id)', backref='teacher', lazy='dynamic')

    def __repr__(self):
        return '<Teacher {}: {}>'.format(self.id, self.name)

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
    def url(self):
        return url_for('teacher.view_profile', teacher_id=self.id)

    @property
    def link(self):
        return Markup('<a href="' + self.url + '">') + Markup.escape(self.name) + Markup('</a>')

    @property
    def image(self):
        if self._image:
            return '/uploads/images/' + self._image
        return '/static/image/teacher.jpg'

    def set_image(self, image):
        self._image = image

    def save(self):
        self.last_edit_time = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def save_without_edit(self):
        db.session.add(self)
        db.session.commit()

    @property
    def info_history(self):
        return self._info_history.all()

    @property
    def info_history_count(self):
        return len(self.info_history)

    @classmethod
    def QUERY_ORDER(self, teacher_rate):
        avg_rate = db.session.query(db.func.avg(Review.rate)).as_scalar()
        avg_rate_count = db.session.query(db.func.count(Review.id) / db.func.count(db.func.distinct(Review.course_id))).as_scalar()
        normalized_rate = (teacher_rate + avg_rate * avg_rate_count) / (CourseRate.review_count + avg_rate_count)
        return normalized_rate


class ThirdPartySigninHistory(db.Model):
    __tablename__ = 'third_party_signin_history'

    id = db.Column(db.Integer,primary_key=True)

    user_id = db.Column(db.Integer)
    email = db.Column(db.String(255))
    from_app = db.Column(db.String(255))
    next_url = db.Column(db.String(255))
    challenge = db.Column(db.String(255))
    token = db.Column(db.String(255))

    signin_time = db.Column(db.DateTime, default=datetime.utcnow)
    verify_time = db.Column(db.DateTime, default=None)

    def add(self):
        db.session.add(self)
        db.session.commit()
