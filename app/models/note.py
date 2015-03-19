from datetime import datetime
from flask import url_for,abort
from app import db



class Note(db.Model):
    __tablename__ = 'notes'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    sno = db.Column(db.String(20), db.ForeignKey('users.id')
    cno = db.Column(db.String(80), db.ForeignKey('courses.id'))
    upvote = db.Column(db.Integer())
    title = db.Column(db.String(200))
    content = db.Column(db.Text())

    publish_time = db.Column(db.DateTime(),default=datetime.utcnow)
    update_time = db.Colmun(db.DateTime,default=datetime.utcnow)

    course = db.relationship('Course',backref='notes')
    author = db.relationship('User',backref='notes')
    comments = db.relationship('NoteComment', backref='note')

    def __init__(self, author, cno, title, content):
        self.sno = author
        self.cno = cno
        self.upvote = 0
        self.title = title
        self.content = content
        self.publish_time = datetime.now()

class NoteComment(db.Model):
    __tablename__ = 'note_comments'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    note_id = db.Column(db.Integer, db.ForeignKey('notes.id'))
    author_id = db.Column(db.String(20), db.ForeignKey('users.id'))
    content = db.Column(db.Text())
    publish_time = db.Column(db.DateTime(), default=datetime.utcnow)
    update_time = db.Colmun(db.DateTime,default=datetime.utcnow)

    author = db.relationship('User')

    def __init__(self, note_id, author, content):
        self.note_id = note_id
        self.sno = author
        self.content = content


