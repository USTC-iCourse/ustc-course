#!/usr/bin/env python3
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKeyConstraint
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'
db = SQLAlchemy(app)

# Students could login
class Student(db.Model):
    sno = db.Column(db.String(20), unique=True, primary_key=True)
    name = db.Column(db.String(80))
    dept = db.Column(db.String(80))

    email = db.Column(db.String(80))
    password = db.Column(db.String(80))
    is_admin = db.Column(db.Boolean(), default=False)

    description = db.Column(db.Text())
    register_time = db.Column(db.DateTime(), default=datetime.utcnow)
    last_login_time = db.Column(db.DateTime())
    # We need "use_alter" to avoid circular dependency in FOREIGN KEYs between Student and ImageStore
    avatar = db.Column(db.Integer, db.ForeignKey('image_store.id', name='avatar_storage', use_alter=True))

    classes_joined = db.relationship('JoinClass', backref='student')
    courses_following = db.relationship('FollowCourse', backref='student')
    reviews = db.relationship('CourseReview')
    notes = db.relationship('CourseNote')
    discussions = db.relationship('CourseForumThread')
    shares = db.relationship('CourseShare')

    def __init__(self, sno, name, dept):
        self.sno = sno
        self.name = name
        self.dept = dept

    def __repr__(self):
        return '<Student {} ({})>'.format(self.name, self.sno)

    # course_type: 计划必修，自由选修……
    def joinClass(self, sno, term, course_type):
        c = JoinClass(sno, cno, term, course_type)
        db.session.add(c)
        db.session.commit()

    def followCourse(self, sno, cno):
        c = FollowCourse(sno, cno)
        db.session.add(c)
        db.session.commit()

class Teacher(db.Model):
    tno = db.Column(db.String(20), unique=True, primary_key=True)
    name = db.Column(db.String(80))
    dept = db.Column(db.String(80))

    email = db.Column(db.String(80))
    description = db.Column(db.Text())

    classes = db.relationship('Class')

    def __init__(self, tno, name, dept):
        self.tno = tno
        self.name = name
        self.dept = dept
    
    def __repr__(self):
        return '<Teacher {} ({})'.format(self.name, self.tno)

# 每个有唯一课程号的课程是一个 Course 对象
class Course(db.Model):
    cid = db.Column(db.Integer, unique=True)
    cno = db.Column(db.String(20), unique=True, primary_key=True)
    name = db.Column(db.String(80))
    dept = db.Column(db.String(80))
    description = db.Column(db.Text())

    classes = db.relationship('Class')
    followers = db.relationship('FollowCourse')

    def __init__(self, cid, cno, name, dept):
        self.cid = cid
        self.cno = cno
        self.name = name
        self.dept = dept

    def __repr__(self):
        return '<Course {} ({})>'.format(self.name, self.cno)

# 每个课程在一个学期开课，是一个 Class 对象。选课信息是与 Class 关联，课程评价、讨论等都是与 Course 关联
class Class(db.Model):
    cno = db.Column(db.String(20), db.ForeignKey('course.cno'), primary_key=True)
    term = db.Column(db.String(10), primary_key=True)
    start_week = db.Column(db.Integer)
    end_week = db.Column(db.Integer)
    tno = db.Column(db.String(20), db.ForeignKey('teacher.tno'))
    credit = db.Column(db.Integer) # 学分
    hours = db.Column(db.Integer)  # 学时
    time = db.Column(db.String(100))
    room = db.Column(db.String(80))

    course = db.relationship('Course')
    teacher = db.relationship('Teacher')
    students = db.relationship('JoinClass', backref='class')

    def __init__(self, cno, term, time, room):
        self.cno = cno
        self.term = term
        self.time = time
        self.room = room

    def __repr__(self):
        return '<Class {} ({}) in {}>'.format(self.course.name, self.cno, self.term)

class JoinClass(db.Model):
    sno = db.Column(db.String(20), db.ForeignKey('student.sno'), primary_key=True)
    cno = db.Column(db.String(80), db.ForeignKey('course.cno'), primary_key=True)
    term = db.Column(db.String(10), primary_key=True)
    course_type = db.Column(db.String(80), primary_key=True)
    __table_args__ = (ForeignKeyConstraint([cno, term], [Class.cno, Class.term]), {})

    course = db.relationship('Course')
    classes = db.relationship('Class')

    def __init__(self, sno, cno, term, course_type):
        self.sno = sno
        self.cno = cno
        self.term = term
        self.course_type = course_type

class FollowCourse(db.Model):
    sno = db.Column(db.String(20), db.ForeignKey('student.sno'), primary_key=True)
    cno = db.Column(db.String(80), db.ForeignKey('course.cno'), primary_key=True)

    def __init__(self, sno, cno):
        self.sno = sno
        self.cno = sno

class CourseReview(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    sno = db.Column(db.String(20), db.ForeignKey('student.sno'))
    cno = db.Column(db.String(80), db.ForeignKey('course.cno'))
    rate = db.Column(db.Integer())   # 课程评分
    upvote = db.Column(db.Integer(), default=0) # 点赞数量
    title = db.Column(db.String(200))
    content = db.Column(db.Text())
    publish_time = db.Column(db.DateTime(), default=datetime.utcnow)

    course = db.relationship('Course')
    student = db.relationship('Student')
    comments = db.relationship('CourseReviewComment', backref='review')

    def __init__(self, author, cno, rate, title, content):
        self.sno = author
        self.cno = cno
        self.rate = rate
        self.upvote = 0
        self.title = title
        self.content = content

class CourseReviewComment(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    review_id = db.Column(db.Integer, db.ForeignKey('course_review.id'))
    sno = db.Column(db.String(20), db.ForeignKey('student.sno'))
    content = db.Column(db.Text())
    publish_time = db.Column(db.DateTime(), default=datetime.utcnow)

    author = db.relationship('Student')

    def __init__(self, review_id, author, content):
        self.review_id = review_id
        self.sno = author
        self.content = content

class CourseNote(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    sno = db.Column(db.String(20), db.ForeignKey('student.sno'))
    cno = db.Column(db.String(80), db.ForeignKey('course.cno'))
    upvote = db.Column(db.Integer())
    title = db.Column(db.String(200))
    content = db.Column(db.Text())
    publish_time = db.Column(db.DateTime())

    course = db.relationship('Course')
    author = db.relationship('Student')
    comments = db.relationship('CourseNoteComment', backref='note')

    def __init__(self, author, cno, title, content):
        self.sno = author
        self.cno = cno
        self.upvote = 0
        self.title = title
        self.content = content
        self.publish_time = datetime.now()

class CourseNoteComment(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    note_id = db.Column(db.Integer, db.ForeignKey('course_note.id'))
    sno = db.Column(db.String(20), db.ForeignKey('student.sno'))
    content = db.Column(db.Text())
    publish_time = db.Column(db.DateTime(), default=datetime.utcnow)

    author = db.relationship('Student')

    def __init__(self, note_id, author, content):
        self.note_id = note_id
        self.sno = author
        self.content = content

class CourseForumThread(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    sno = db.Column(db.String(20), db.ForeignKey('student.sno'))
    cno = db.Column(db.String(80), db.ForeignKey('course.cno'))
    upvote = db.Column(db.Integer(), default=0)
    title = db.Column(db.String(200))
    content = db.Column(db.Text())

    course = db.relationship('Course')
    author = db.relationship('Student')
    posts = db.relationship('CourseForumPost', backref='thread')

    def __init__(self, author, cno, title, content):
        self.sno = author
        self.cno = cno
        self.upvote = 0
        self.title = title
        self.content = content
        self.publish_time = datetime.now()

class CourseForumPost(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('course_forum_thread.id'))
    sno = db.Column(db.Integer, db.ForeignKey('student.sno'))
    upvote = db.Column(db.Integer(), default=0)
    content = db.Column(db.Text())
    publish_time = db.Column(db.DateTime(), default=datetime.utcnow)

    author = db.relationship('Student')

    def __init__(self, thread_id, author, content):
        self.thread_id = thread_id
        self.sno = author
        self.upvote = 0
        self.content = content

class CourseShare(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    sno = db.Column(db.String(20), db.ForeignKey('student.sno'))
    cno = db.Column(db.String(80), db.ForeignKey('course.cno'))
    upvote = db.Column(db.Integer(), default=0)
    filename = db.Column(db.String(256))
    description = db.Column(db.Text())
    stored_filename = db.Column(db.String(80), unique=True)
    publish_time = db.Column(db.DateTime(), default=datetime.utcnow)

    course = db.relationship('Course')
    author = db.relationship('Student')
    comments = db.relationship('CourseShareComment', backref='share')

    def __init__(self, author, cno, title, content):
        self.sno = author
        self.cno = cno
        self.upvote = 0
        self.title = title
        self.content = content

class CourseShareComment(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    share_id = db.Column(db.Integer, db.ForeignKey('course_share.id'))
    sno = db.Column(db.String(20), db.ForeignKey('student.sno'))
    content = db.Column(db.Text())
    publish_time = db.Column(db.DateTime(), default=datetime.utcnow)

    author = db.relationship('Student')

    def __init__(self, share_id, author, content):
        self.share_id = share_id
        self.sno = author
        self.content = content

class ImageStore(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    sno = db.Column(db.String(20), db.ForeignKey('student.sno'))
    filename = db.Column(db.String(256))
    upload_time = db.Column(db.DateTime(), default=datetime.utcnow)
    stored_filename = db.Column(db.String(80), unique=True)

    # we need to specify foreign_keys because Student.avatar => ImageStore.id is another foreign key
    author = db.relationship('Student', foreign_keys=[sno])

    def __init__(self, author, filename, stored_filename):
        self.sno = author
        self.filename = filename
        self.upload_time = datetime.now()
        self.stored_filename = stored_filename

