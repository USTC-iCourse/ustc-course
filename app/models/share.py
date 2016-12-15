from datetime import datetime
from app import db
try:
    from flask_login import current_user
except:
    current_user=None

share_upvotes = db.Table('share_upvotes',
    db.Column('share_id', db.Integer, db.ForeignKey('shares.id'), primary_key=True),
    db.Column('author_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

class Share(db.Model):
    __tablename__ = 'shares'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))

    upvote = db.Column(db.Integer,default=0) #点赞数量
    filename = db.Column(db.String(256))
    description = db.Column(db.Text)
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)
    stored_filename = db.Column(db.String(80), unique=True)

    upvote_count = db.Column(db.Integer, default=0)
    comment_count = db.Column(db.Integer, default=0)

    author = db.relationship('User', backref='shares')
    #:course: backref to Course
    upvotes = db.relationship('User', secondary=share_upvotes)
    comments = db.relationship('ShareComment', backref='share')

class ShareComment(db.Model):
    __tablename__ = 'share_comments'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    share_id = db.Column(db.Integer, db.ForeignKey('shares.id'))

    content = db.Column(db.Text)
    publish_time = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User')
    #:share

