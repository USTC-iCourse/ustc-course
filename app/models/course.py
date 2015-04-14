from datetime import datetime
from flask import url_for,abort
from app import db
from .user import User
try:
    from flask.ext.login import current_user
except:
    current_user=None

class CourseTimeLocation(db.Model):
    __tablename__ = 'course_time_locations'

    # we do not need an ID, but ORM requires it
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    weekday = db.Column(db.Integer)
    begin_hour = db.Column(db.Integer)
    num_hours = db.Column(db.Integer)
    location = db.Column(db.String(80))

    note = db.Column(db.String(200))

course_teachers = db.Table('course_teachers',
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id')),
    db.Column('teacher_id', db.Integer, db.ForeignKey('teachers.id')),
)

class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer,unique=True,primary_key=True)
    cno = db.Column(db.String(20))  # course_no, 课堂号，长的
    courseries = db.Column(db.String(20)) # course_series, 课程编号，短的
    term = db.Column(db.String(10)) # 学年学期，例如 20142 表示 2015 年春季学期
    name = db.Column(db.String(80)) # 课程名称
    kcid = db.Column(db.Integer)    # 课程id
    dept = db.Column(db.String(80)) # 开课单位

    course_major = db.Column(db.String(20)) # 学科类别
    course_type = db.Column(db.String(20)) # 课程类别，计划内，公选课……
    course_level = db.Column(db.String(20)) # 课程层次
    grading_type = db.Column(db.String(20)) # 评分制
    teaching_material = db.Column(db.Text) # 教材
    reference_material = db.Column(db.Text) # 参考书
    student_requirements = db.Column(db.Text) # 预修课程
    description = db.Column(db.Text()) # 课程简介
    description_eng = db.Column(db.Text()) # 英文简介

    credit = db.Column(db.Integer) # 学分
    hours = db.Column(db.Integer)  # 学时
    hours_per_week = db.Column(db.Integer) # 周学时
    class_numbers = db.Column(db.String(200)) # 上课班级
    start_week = db.Column(db.Integer)  # 起始周
    end_week = db.Column(db.Integer) # 终止周
    time_locations = db.relationship('CourseTimeLocation', backref='course')

    __table_args__ = (db.UniqueConstraint('cno', 'term'), )

    teachers = db.relationship('Teacher', secondary=course_teachers, backref='courses')
    #:followers : backref to User
    #students : backref to Student
    reviews = db.relationship('CourseReview',backref='course',lazy='dynamic')
    notes = db.relationship('CourseNote', backref='course',lazy='dynamic')
    #upvote_count = db.Column(db.Integer) #推荐人数

    #posts = db.relationship('CourseForumPost')
    _course_rate = db.relationship('CourseRate',backref='course',uselist=False)

    def __repr__(self):
        return '<Course %s(%s)>'%(self.name,self.cno)

    @classmethod
    def create(cls,cno,term,**kwargs):
        if cls.query.filter_by(cno=cno,term=term).first():
            return None
        course = Course(cno=cno,term=term,**kwargs)
        course.course_rate = CourseRate()
        db.session.add(course)
        db.session.commit()
        return course

    @property
    def course_rate(self):
        if self._course_rate:
            return self._course_rate
        else:
            self._course_rate =  CourseRate()
            self.save()
            return self._course_rate

    @property
    def url(self):
        return url_for('course.view_course',course_id=self.id,course_name=self.name)

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    @property
    def teacher(self):
        if len(self.teachers) >= 1:
            return self.teachers[0]
        else:
            return None

    @property
    def related_courses(self):
        '''return the courses that are the same name'''
        return self.query.filter_by(name=self.name).all()

    @property
    def history_courses(self):
        '''returns the courses having the same course number'''
        return self.query.filter_by(courseries=self.courseries).all()

    @property
    def time_locations_display(self):
        return [ row.location + ': ' + row.time ].join('; ')

    @property
    def term_display(self):
        if self.term[4] == '1':
            return self.term[0:4] + '秋'
        elif self.term[4] == '2':
            return str(int(self.term[0:4])+1) + '春'
        elif self.term[4] == '3':
            return str(int(self.term[0:4])+1) + '夏'
        else:
            return 'unkown'

    @property
    def course_major_display(self):
        if self.course_major == None:
            return '未知'


review_upvotes = db.Table('review_upvotes',
    db.Column('review_id', db.Integer, db.ForeignKey('course_reviews.id'), primary_key=True),
    db.Column('author_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

class CourseRate(db.Model):
    __tablename__ = 'course_rates'

    id = db.Column(db.Integer, db.ForeignKey('courses.id'), primary_key=True)
    _difficulty_total = db.Column(db.Integer,default=0)
    _homework_total = db.Column(db.Integer,default=0)
    _grading_total = db.Column(db.Integer,default=0)
    _gain_total = db.Column(db.Integer,default=0)
    _rate_total = db.Column(db.Integer,default=0)
    review_count = db.Column(db.Integer,default=0) #点评数

    @property
    def difficulty(self):
        '''if review count is not 0,
        the mean of the difficulty will be returned.
        Otherwise, None will be returned .'''
        mapper = {1:'简单',
                2:'中等',
                3:'困难'}
        if self.review_count:
            rank = self._difficulty_total/self.review_count
            return mapper[round(rank)]
        return None

    @property
    def homework(self):
        mapper = {1:'很少',
                2:'中等',
                3:'很多'}
        if self.review_count:
            rank = round(self._homework_total/self.review_count)
            return mapper[rank]
        return None

    @property
    def grading(self):
        mapper = {1:'超好',
                2:'厚道',
                3:'杀手',}
        if self.review_count:
            rank = round(self._grading_total/self.review_count)
            return mapper[rank]
        return None

    @property
    def gain(self):
        mapper = {1:'很多',
                2:'一般',
                3:'没有'}
        if self.review_count:
            rank = round(self._gain_total/self.review_count)
            return mapper[rank]
        return None

    @property
    def rate(self):
        if self.review_count:
            res = round(self._rate_total/self.review_count)
            return res
        return None

    def save(self):
        db.session.add(self)
        db.session.commit()

    def add(self,difficulty,homework,grading,gain,rate):
        self.review_count += 1
        self._difficulty_total += difficulty
        self._homework_total += homework
        self._grading_total += grading
        self._gain_total += gain
        self._rate_total += rate
        self.save()

    def subtract(self,difficulty,homework,grading,gain,rate):
        self.review_count -= 1
        self.difficulty -= difficulty
        self.homework -= homework
        self.grading -= grading
        self.gain -= gain
        self.rate -= rate
        self.save()


class CourseReview(db.Model):
    __tablename__ = 'course_reviews'
    id = db.Column(db.Integer,primary_key=True, unique=True)

    difficulty = db.Column(db.Integer,db.CheckConstraint('difficulty>=1 and difficulty<=3'))
    homework = db.Column(db.Integer,db.CheckConstraint('homework>=1 and homework<=3'))
    grading = db.Column(db.Integer,db.CheckConstraint('grading>=1 and grading<=3'))
    gain = db.Column(db.Integer,db.CheckConstraint('gain>=1 and gain<=3'))
    rate = db.Column(db.Integer,db.CheckConstraint('rate>=1 and rate<=10'))  #课程评分
    content = db.Column(db.Text())

    publish_time = db.Column(db.DateTime(),default=datetime.utcnow)
    update_time = db.Column(db.DateTime(),default=datetime.utcnow)

    upvote = db.Column(db.Integer,default=0) #点赞数量
    upvotes = db.relationship('User', secondary=review_upvotes)
    comments = db.relationship('CourseReviewComment',backref='review')

    author = db.relationship('User',backref='reviews')
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    #course: Course


    def add(self):
        '''crete a new review'''
        if self.course and self.author:
            course_rate = self.course.course_rate
            course_rate.add(self.difficulty,
                    self.homework,
                    self.grading,
                    self.gain,
                    self.rate)
            db.session.add(self)
            db.session.commit()
            return self
        return None

    def delete(self):
        if not self.id:
            return None
        course_rate = self.course.course_rate
        course_rate.subtract(self.difficulty,
                self.homework,
                self.grading,self.gain,
                self.rate)
        db.session.delete(self)
        db.session.commit()

    def update(self,difficulty,
            homework,
            grading,
            gain,
            rate,
            content):
        course_rate = self.course.course_rate
        course_rate.subtract(self.difficulty,
                self.homework,
                self.grading,
                self.gain,
                self.rate)
        course_rate.add(difficulty,homework,grading,gain,rate)
        self.content = content
        self.update_time = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

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
    #:review: backref to CourseReview

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
    posts = db.relationship('CourseForumPost',backref='thread',lazy='dynamic')

    upvotes = db.relationship('User', secondary=forum_thread_upvotes)

forum_post_upvotes = db.Table('forum_post_upvotes',
    db.Column('post_id', db.Integer, db.ForeignKey('course_forum_posts.id'), primary_key=True),
    db.Column('author_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

class CourseForumPost(db.Model):
    __tablename__ = 'course_forum_posts'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    thread_id = db.Column(db.Integer, db.ForeignKey('course_forum_threads.id'))

    upvote = db.Column(db.Integer,default=0) #点赞数量
    content = db.Column(db.Text)
    publish_time = db.Column(db.DateTime, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User')
    upvotes = db.relationship('User', secondary=forum_post_upvotes)

    def save(self, thread, author=current_user):
        if thread and author:
            self.thread = thread
            self.author = author
            db.session.add(self)
            db.session.commit()

