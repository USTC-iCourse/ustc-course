from datetime import datetime

from flask import url_for,abort
from app import db




# 每个有唯一课程号的课程是一个 Course 对象
class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer,unique=True,primary_key=True)
    cno = db.Column(db.String(20), unique=True)
    term = db.Column(db.String(10))
    name = db.Column(db.String(80))
    dept = db.Column(db.String(80))
    description = db.Column(db.Text())

    tno = db.Column(db.String(20), db.ForeignKey('teacher.tno'))
    credit = db.Column(db.Integer) # 学分
    hours = db.Column(db.Integer)  # 学时
    default_classes = db.Column(db.String(200))
    start_end_week = db.Column(db.String(100))
    time_location = db.Column(db.String(100))

    #teacher : Teacher
    #followers : Students that follow the class
    #students : Students that attend the class
    reviews = db.relationship('CourseReview',backref='course')
    #notes

    def __init__(self,  cno, name, dept):
        #self.cid = cid
        self.cno = cno
        self.name = name
        self.dept = dept

    def __repr__(self):
        return '<Course {} ({})>'.format(self.name, self.cno)

class CourseReview(db.Model):
    __tablename__ = 'course_reviews'
    id = db.Column(db.Integer,primary_key=True, unique=True)
    author_id = db.Column(db.String(20),db.ForeignKey('students.sno'))
    course_id = db.Column(db.String(20),db.ForeignKey('courses.id'))

    rate = db.Column(db.Integer)  #课程评分
    upvote = db.Column(db.Integer,default=0) #点赞数量
#TODO: upvote lists
    title = db.Column(db.String(200))
    content = db.Column(db.Text())
    publish_time = db.Column(db.DateTime(),default=datetime.utcnow)
    update_time = db.Column(db.DateTime(),default=datetime.utcnow)

    author = db.relationship('Student',backref='reviews')
    #course

    comments = db.relationship('CourseReviewComment',backref='review')

    def __init__(self,author,course,rate,title,content):
        self.author = author
        self.course = course
        self.rate = rate
        self.title = title
        self.content = content

class CourseReviewComment(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    review_id = db.Column(db.Integer, db.ForeignKey('course_reviews.id'))
    author_id = db.Column(db.String(20), db.ForeignKey('students.sno'))
    author = db.relationship('Student')
    content = db.Column(db.Text)
    publish_time = db.Column(db.DateTime,default=datetime.utcnow)

    def __init__(self,review, author, content):
        self.review = review
        self.author = author
        self.content = content




