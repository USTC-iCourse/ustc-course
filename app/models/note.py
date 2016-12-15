from datetime import datetime
from app import db
try:
    from flask_login import current_user
except:
    current_user=None

note_upvotes = db.Table('note_upvotes',
    db.Column('note_id', db.Integer, db.ForeignKey('notes.id'), primary_key=True),
    db.Column('author_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

class Note(db.Model):
    __tablename__ = 'notes'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))
    term = db.Column(db.String(10), index=True)

    title = db.Column(db.String(200))
    content = db.Column(db.Text())
    publish_time = db.Column(db.DateTime(),default=datetime.utcnow)
    update_time = db.Column(db.DateTime(),default=datetime.utcnow)

    upvote_count = db.Column(db.Integer,default=0) #点赞数量
    comment_count = db.Column(db.Integer, default=0)

    upvotes = db.relationship('User', secondary=note_upvotes)
    author = db.relationship('User', backref='notes')
    #:course: backref to Course
    comments = db.relationship('NoteComment', backref='note')

class NoteComment(db.Model):
    __tablename__ = 'note_comments'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    note_id = db.Column(db.Integer, db.ForeignKey('notes.id'))
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    content = db.Column(db.Text)
    publish_time = db.Column(db.DateTime, default=datetime.utcnow)

    author = db.relationship('User')
    #:note: backref to Note

