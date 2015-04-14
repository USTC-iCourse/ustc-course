from app import db
from datetime import datetime

class ImageStore(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    filename = db.Column(db.String(256))
    upload_time = db.Column(db.DateTime(), default=datetime.utcnow)
    stored_filename = db.Column(db.String(80), unique=True)

    def __init__(self, author, filename, stored_filename):
        self.author = author
        self.filename = filename
        self.upload_time = datetime.now()
        self.stored_filename = stored_filename
