from datetime import datetime
from app import db
try:
    from flask.ext.login import current_user
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

    upvotes = db.relationship('User', secondary=review_upvotes)
    comments = db.relationship('ReviewComment',backref='review')

    author = db.relationship('User', backref='reviews')
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
        review = cls(**kwargs)
        review.save()


class ReviewComment(db.Model):
    __tablename__ = 'review_comments'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    review_id = db.Column(db.Integer, db.ForeignKey('reviews.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    content = db.Column(db.Text)
    publish_time = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User')
    #:review: backref to Review

