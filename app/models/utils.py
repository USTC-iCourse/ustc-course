from flask import url_for
from app import db
from datetime import datetime

class ImageStore(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    sno = db.Column(db.String(20), db.ForeignKey('student.sno'))
    filename = db.Column(db.String(256))
    upload_time = db.Column(db.DateTime(), default=datetime.utcnow)
    stored_filename = db.Column(db.String(80), unique=True)
    # we need to specify foreign_keys because Student.avatar => ImageStore.id is another       foreign key
    author = db.relationship('Student', foreign_keys=[sno])
    def __init__(self, author, filename, stored_filename):
        self.sno = author
        self.filename = filename
        self.upload_time = datetime.now()
        self.stored_filename = stored_filename

