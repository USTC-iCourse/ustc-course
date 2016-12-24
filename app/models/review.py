from flask import url_for, Markup
from datetime import datetime
from app import db
import html2text
try:
    from flask_login import current_user
except:
    current_user=None

review_upvotes = db.Table('review_upvotes',
    db.Column('review_id', db.Integer, db.ForeignKey('reviews.id'), primary_key=True),
    db.Column('author_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer,primary_key=True, unique=True)

    difficulty = db.Column(db.Integer,db.CheckConstraint('difficulty>=1 and difficulty<=3'))
    homework = db.Column(db.Integer,db.CheckConstraint('homework>=1 and homework<=3'))
    grading = db.Column(db.Integer,db.CheckConstraint('grading>=1 and grading<=3'))
    gain = db.Column(db.Integer,db.CheckConstraint('gain>=1 and gain<=3'))
    rate = db.Column(db.Integer,db.CheckConstraint('rate>=1 and rate<=10'))  #课程评分
    content = db.Column(db.Text())

    publish_time = db.Column(db.DateTime(),default=datetime.utcnow)
    update_time = db.Column(db.DateTime(),default=datetime.utcnow)

    upvote_count = db.Column(db.Integer, default=0) #点赞数量
    comment_count = db.Column(db.Integer, default=0)

    upvote_users = db.relationship('User', secondary=review_upvotes)
    comments = db.relationship('ReviewComment', backref='review', lazy='joined')

    author = db.relationship('User', backref=db.backref('reviews', order_by='desc(Review.publish_time)'), lazy='joined')
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    term = db.Column(db.String(10), index=True)

    is_hidden = db.Column(db.Boolean, default=False)
    #course: Course

    def add(self):
        '''crete a new review'''
        if self.course and self.author:
            # Make sure that each user can only add one review for each course
            if self.author in self.course.review_users:
                return None
            course_rate = self.course.course_rate
            course_rate.add(self.difficulty,
                    self.homework,
                    self.grading,
                    self.gain,
                    self.rate)
            self.course.review_users.append(self.author)
            db.session.add(self.course)
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
        self.course.review_users.remove(self.author)
        db.session.commit()

    # self and old must have the same course_id
    def update_course_rate(self,old):
        course_rate = self.course.course_rate
        course_rate.subtract(old.difficulty,
                old.homework,
                old.grading,
                old.gain,
                old.rate)
        course_rate.add(self.difficulty,
                self.homework,
                self.grading,
                self.gain,
                self.rate)
        db.session.commit()

    def upvote(self,author=current_user):
        if author in self.upvote_users:
            return False,"The user has upvoted!"
        self.upvote_users.append(author)
        self.upvote_count +=1
        self.__save()
        return True,"Success!"

    def cancel_upvote(self,author=current_user):
        if author not in self.upvote_users:
            return (False,"The user has not upvoted!")
        self.upvote_users.remove(author)
        self.upvote_count -=1
        self.__save()
        return (True,"Success!")

    def is_upvoted(self, user=current_user):
        return user in self.upvote_users

    def hide(self):
        self.is_hidden = True
        self.__save()
        return (True,"Success!")

    def unhide(self):
        self.is_hidden = False
        self.__save()
        return (True,"Success!")

    # this will create a new object, do not use it for update
    def __save(self):
        db.session.add(self)
        db.session.commit()

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
        review = cls(**kwargs)
        review.__save()

    @property
    def url(self):
        return url_for('course.view_course', course_id=self.course_id) + '#review-' + str(self.id)

    @property
    def link(self):
        return Markup('<a href="' + self.url + '">') + Markup.escape(self.course.name) + Markup('</a>')

    @property
    def content_text(self):
        return html2text.html2text(self.content)

    @property
    def term_display(self):
        if self.term[4] == '1':
            return self.term[0:4] + '秋'
        elif self.term[4] == '2':
            return str(int(self.term[0:4])+1) + '春'
        elif self.term[4] == '3':
            return str(int(self.term[0:4])+1) + '夏'
        else:
            return '未知'


class ReviewComment(db.Model):
    __tablename__ = 'review_comments'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    review_id = db.Column(db.Integer, db.ForeignKey('reviews.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    content = db.Column(db.Text)
    publish_time = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User')
    #:review: backref to Review

    def add(self,review,content,author=current_user):
        self.content = content
        self.review = review
        review.comment_count += 1
        self.author = author
        db.session.add(self)
        db.session.commit()
        return True,"Success!"

    def delete(self):
        if self.review:
            review = self.review
            review.comments.remove(self)
            review.comment_count -= 1
            db.session.add(review)
            db.session.commit()
        db.session.delete(self)
        db.session.commit()
        return True,"Success"

    @property
    def url(self):
        return self.review.url

    @property
    def link(self):
        return self.review.link
