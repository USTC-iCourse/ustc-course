from app import db
from datetime import datetime
try:
    from flask_login import current_user
except:
    current_user=None

class ImageStore(db.Model):
    __tablename__ = 'image_store'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    filename = db.Column(db.String(256))
    upload_time = db.Column(db.DateTime(), default=datetime.utcnow)
    stored_filename = db.Column(db.String(80), unique=True)

    author = db.relationship('User', foreign_keys='ImageStore.author_id', uselist=False)

    def __init__(self, filename, stored_filename, author=current_user):
        if author:
            self.author = author
            self.filename = filename
            self.upload_time = datetime.now()
            self.stored_filename = stored_filename

    def save(self):
        db.session.add(self)
        db.session.commit()

