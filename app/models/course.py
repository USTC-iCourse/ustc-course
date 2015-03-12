from datetime import datetime

from flask import url_for,abort
from app import db




# 每个有唯一课程号的课程是一个 Course 对象
class Course(db.Model):
    __tablename__ = 'courses'

    cno = db.Column(db.String(20), unique=True, primary_key=True)
    name = db.Column(db.String(80))
    dept = db.Column(db.String(80))
    description = db.Column(db.Text())

    classes = db.relationship('Class',backref='course',lazy='dynamic')
    #followers = db.relationship('Student',sencondary=followers,
    #        backref=db.backref('courses',lazy='dynamic'),lazy='dynamic')

    def __init__(self,  cno, name, dept):
        #self.cid = cid
        self.cno = cno
        self.name = name
        self.dept = dept

    def __repr__(self):
        return '<Course {} ({})>'.format(self.name, self.cno)

# 每个课程在一个学期开课，是一个 Class 对象。选课信息是与 Class 关联，课程评价、讨论等都是与 Course 关联
class Class(db.Model):
    __tablename__ = 'classes'

    id = db.Column(db.Integer, unique=True,primary_key=True)
    cno = db.Column(db.String(20), db.ForeignKey('course.cno'))
    term = db.Column(db.String(10))
    start_week = db.Column(db.Integer)
    end_week = db.Column(db.Integer)
    credit = db.Column(db.Integer) # 学分
    hours = db.Column(db.Integer)  # 学时
    time = db.Column(db.String(100))
    room = db.Column(db.String(80))

    #course = db.relationship('Course')
    cno = db.Column(db.String(20), db.ForeignKey('courses.cno'), primary_key=True)
    #teacher = db.relationship('Teacher')
    tno = db.Column(db.String(20), db.ForeignKey('teachers.tno'))
    #students = db.relationship('JoinClass', backref='class')

    def __init__(self, cno, term, time, room):
        self.cno = cno
        self.term = term
        self.time = time
        self.room = room

    def __repr__(self):
        return '<Class {} ({}) in {}>'.format(self.course.name, self.cno, self.term)



