from datetime import datetime
from flask import url_for,abort
from app import db
from .user import User
try:
    from flask.ext.login import current_user
except:
    current_user=None

course_time_locations = db.Table('course_time_locations',
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id')),
    db.Column('time', db.String(20)),
    db.Column('location', db.String(20))
)

class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer,unique=True,primary_key=True)
    cno = db.Column(db.String(20))  # 课堂号
    term = db.Column(db.String(10)) # 学年学期，例如 20142 表示 2015 年春季学期
    name = db.Column(db.String(80)) # 课程名称
    kcid = db.Column(db.Integer)    # 课程id
    dept = db.Column(db.String(80)) # 开课院系
    description = db.Column(db.Text()) # 课程描述

    credit = db.Column(db.Integer) # 学分
    hours = db.Column(db.Integer)  # 学时
    class_numbers = db.Column(db.String(200))   # 上课班级
    start_end_week = db.Column(db.String(100))  # 起止周
    time_locations = db.relationship('Course', secondary=course_time_locations)

    __table_args__ = (db.UniqueConstraint('cno', 'term'), )

    teacher = db.relationship('Teacher',backref='courses')
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'))
    #:followers : backref to User
    #students : backref to Student
    reviews = db.relationship('CourseReview',backref='course',lazy='dynamic')
    notes = db.relationship('CourseNote', backref='course',lazy='dynamic')

    #posts = db.relationship('CourseForumPost')

    def __repr__(self):
        return '<Course %s(%s)>'%(self.name,self.cno)

    @classmethod
    def create(cls,cno,term,**kwargs):
        if cls.query.filter_by(cno=cno,term=term).first():
            return None
        course = Course(cno=cno,term=term,**kwargs)
        db.session.add(course)
        db.session.commit()
        return course

    @property
    def url(self):
        return url_for('course.view_course',course_id=self.id,course_name=self.name)

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    @property
    def related_courses(self):
        '''return the courses that are the same name'''
        return self.query.filter_by(name=self.name).all()

    @property
    def history_courses(self):
        '''returns the courses having the same course number'''
        return self.query.filter_by(cno=self.cno).all()

review_upvotes = db.Table('review_upvotes',
    db.Column('review_id', db.Integer, db.ForeignKey('course_reviews.id'), primary_key=True),
    db.Column('author_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

class CourseReview(db.Model):
    __tablename__ = 'course_reviews'
    id = db.Column(db.Integer,primary_key=True, unique=True)

    rate = db.Column(db.Integer)  #课程评分
    upvote = db.Column(db.Integer,default=0) #点赞数量
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))

    rate = db.Column(db.Integer)  #课程评分
    title = db.Column(db.String(200))
    content = db.Column(db.Text())
    publish_time = db.Column(db.DateTime(),default=datetime.utcnow)
    update_time = db.Column(db.DateTime(),default=datetime.utcnow)

    author = db.relationship('User',backref='reviews')
    upvotes = db.relationship('User', secondary=review_upvotes)
    comments = db.relationship('CourseReviewComment',backref='review')

    def save(self):
        if self.id:     # the review already exits
            self.update_time = datetime.utcnow()
            db.session.add(self)
            db.session.commit()
            return self

        if self.course and self.author:
            db.session.add(self)
            db.session.commit()
            return self
        return None

    def add_comment(self, comment, author=current_user):
        self.comments.append(comment)
        self.save()

    @classmethod
    def create(cls,**kwargs):
        course_id = kwargs.get('course_id')
        if course_id:
            course = Course.query.get(course_id)
            kwargs['course'] = course
        author_id = kwargs.get('author_id')
        if author_id:
            author = User.query.get(author_id)
            kwargs['author'] = author
        course_review = cls(**kwargs)
        course_review.save()


class CourseReviewComment(db.Model):
    __tablename__ = 'course_review_comments'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    review_id = db.Column(db.Integer, db.ForeignKey('course_reviews.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    content = db.Column(db.Text)
    publish_time = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User')
    #review = db.relationship('CourseReview')

note_upvotes = db.Table('note_upvotes',
    db.Column('note_id', db.Integer, db.ForeignKey('course_notes.id'), primary_key=True),
    db.Column('author_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

class CourseNote(db.Model):
    __tablename__ = 'course_notes'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))

    upvote = db.Column(db.Integer,default=0) #点赞数量
    title = db.Column(db.String(200))
    content = db.Column(db.Text())
    publish_time = db.Column(db.DateTime(),default=datetime.utcnow)
    update_time = db.Column(db.DateTime(),default=datetime.utcnow)

    upvotes = db.relationship('User', secondary=note_upvotes)
    author = db.relationship('User')
    #:course: backref to Course
    comments = db.relationship('CourseNoteComment', backref='note')

class CourseNoteComment(db.Model):
    __tablename__ = 'course_note_comments'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    note_id = db.Column(db.Integer, db.ForeignKey('course_notes.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    content = db.Column(db.Text)
    publish_time = db.Column(db.DateTime, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User')
    #:note: backref to CourseNote


forum_thread_upvotes = db.Table('forum_thread_upvotes',
    db.Column('thread_id', db.Integer, db.ForeignKey('course_forum_threads.id'), primary_key=True),
    db.Column('author_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)


class CourseForumThread(db.Model):
    __tablename__ = 'course_forum_threads'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))

    upvote = db.Column(db.Integer,default=0) #点赞数量
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    publish_time = db.Column(db.DateTime, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User')
    course = db.relationship('Course')
    posts = db.relationship('CourseForumPost',backref='course_forum_thread',lazy='dynamic')

    upvotes = db.relationship('User', secondary=forum_thread_upvotes)
    def save(self, review, author=current_user):
        if review and author:
            self.review = review
            self.author = author
            db.session.add(self)
            db.session.commit()


class CourseForumPost(db.Model):
    __tablename__ = 'course_forum_posts'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    thread_id = db.Column(db.Integer, db.ForeignKey('course_forum_threads.id'))

    upvote = db.Column(db.Integer,default=0) #点赞数量
    content = db.Column(db.Text)
    publish_time = db.Column(db.DateTime, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, default=datetime.utcnow)

    thread = db.relationship('CourseForumThread')
    author = db.relationship('User')
