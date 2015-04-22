from datetime import datetime
from flask import url_for
from app import db
from .user import User
from decimal import Decimal
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
    term = db.Column(db.String(10), index=True) # 学年学期，例如 20142 表示 2015 年春季学期
    name = db.Column(db.String(80), index=True) # 课程名称
    kcid = db.Column(db.Integer)    # 课程id
    dept = db.Column(db.String(80), index=True) # 开课单位

    course_major = db.Column(db.String(20)) # 学科类别
    course_type = db.Column(db.String(20)) # 课程类别，计划内，公选课……
    course_level = db.Column(db.String(20)) # 课程层次
    grading_type = db.Column(db.String(20)) # 评分制
    teaching_material = db.Column(db.Text) # 教材
    reference_material = db.Column(db.Text) # 参考书
    student_requirements = db.Column(db.Text) # 预修课程
    description = db.Column(db.Text()) # 课程简介
    description_eng = db.Column(db.Text()) # 英文简介
    homepage = db.Column(db.Text) # 课程主页

    credit = db.Column(db.Integer) # 学分
    hours = db.Column(db.Integer)  # 学时
    hours_per_week = db.Column(db.Integer) # 周学时
    class_numbers = db.Column(db.String(200)) # 上课班级
    start_week = db.Column(db.Integer)  # 起始周
    end_week = db.Column(db.Integer) # 终止周
    _image = db.Column(db.String(100))

    time_locations = db.relationship('CourseTimeLocation', backref='course')

    __table_args__ = (db.UniqueConstraint('cno', 'term'), )

    teachers = db.relationship('Teacher', secondary=course_teachers, backref=db.backref('courses',lazy='dynamic'),lazy="joined")
    reviews = db.relationship('Review', backref='course', lazy='dynamic')
    notes = db.relationship('Note', backref='course', lazy='dynamic')
    forum_threads = db.relationship('ForumThread', backref='course', lazy='dynamic')
    shares = db.relationship('Share', backref='course', lazy='dynamic')

    #students  : backref to Student
    #followers : backref to User
    #upvote_users: backref to User
    #downvote_users: backref to User

    _course_rate = db.relationship('CourseRate', backref='course', uselist=False, lazy='joined')

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
    def rate(self):
        return self.course_rate

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

    @property
    def review_count(self):
        return self.course_rate.review_count

    @property
    def upvote_count(self):
        return self.course_rate.upvote_count

    @property
    def downvote_count(self):
        return self.course_rate.downvote_count

    def upvote(self,user=current_user):
        user.courses_upvoted.append(self)
        self.course_rate.upvote_count += 1
        db.session.add(self)
        db.session.add(user)
        db.session.commit()
        return True
        return False

    def un_upvote(self,user=current_user):
        user.courses_upvoted.remove(self)
        self.course_rate.upvote_count -= 1
        db.session.add(self)
        db.session.add(user)
        db.session.commit()

    def downvote(self,user=current_user):
        user.courses_downvoted.append(self)
        self.course_rate.downvote_count += 1
        db.session.add(self)
        db.session.add(user)
        db.session.commit()
        return True

    def un_downvote(self,user=current_user):
        user.courses_downvoted.remove(self)
        self.course_rate.downvote_count -= 1
        db.session.add(self)
        db.session.add(user)
        db.session.commit()
        return True

    @property
    def voted(self,user=current_user):
        if user in self.upvote_users or user in self.downvote_users:
            return True
        return False

    @property
    def upvoted(self,user=current_user):
        if user in self.upvote_users:
            return True
        return False

    @property
    def downvoted(self,user=current_user):
        if user in self.downvote_users:
            return True
        return False

    def follow(self, user=current_user):
        if user in self.followers:
            return False
        self.followers.append(user)
        self.course_rate.follow_count += 1
        db.session.commit()
        return True

    def unfollow(self, user=current_user):
        if not user in self.followers:
            return False
        self.followers.remove(user)
        self.course_rate.follow_count -= 1
        db.session.commit()
        return True

    @property
    def following(self, user=current_user):
        if user in self.followers:
            return True
        else:
            return False

    @property
    def follow_count(self):
        return self.course_rate.follow_count

    @property
    def student_count(self):
        return len(self.students)

    def join(self):
        if not user.is_student or user.info in self.students:
            return False
        self.students.append(user.info)
        db.session.commit()
        return True

    def quit(self):
        if not user.is_student or not user.info in self.students:
            return False
        self.students.remove(user.info)
        db.session.commit()
        return True

    @property
    def teachers_count(self):
        return len(self.teachers)

    @property
    def teacher_names_display(self):
        if self.teachers_count == 0:
            return 'Unknown'
        else:
            return ', '.join([teacher.name for teacher in self.teachers])

    @property
    def image(self):
        if self._image:
            return '/uploads/images/' + self._image
        return '/static/image/user.png'


class CourseRate(db.Model):
    __tablename__ = 'course_rates'

    id = db.Column(db.Integer, db.ForeignKey('courses.id'), primary_key=True)
    _difficulty_total = db.Column(db.Integer,default=0)
    _homework_total = db.Column(db.Integer,default=0)
    _grading_total = db.Column(db.Integer,default=0)
    _gain_total = db.Column(db.Integer,default=0)
    _rate_total = db.Column(db.Integer,default=0)
    review_count = db.Column(db.Integer,default=0) #点评数
    upvote_count = db.Column(db.Integer,default=0) #推荐人数
    downvote_count = db.Column(db.Integer,default=0) #不推荐人数
    follow_count = db.Column(db.Integer,default=0) #关注人数
    join_count = db.Column(db.Integer,default=0) #加入课程人数

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
    def average_rate(self):
        if self.review_count:
            res = Decimal("%.1f" % (self._rate_total/self.review_count))
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
        self._difficulty_total -= difficulty
        self._homework_total -= homework
        self._grading_total -= grading
        self._gain_total -= gain
        self._rate_total -= rate
        self.save()

