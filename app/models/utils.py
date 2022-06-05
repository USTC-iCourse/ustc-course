from app import db
from datetime import datetime

class RevokedToken(db.Model):
    value = db.Column(db.String(100), unique=True, primary_key=True)
    revoke_time = db.Column(db.DateTime(), default=datetime.utcnow())

    @classmethod
    def add(cls, value):
        token = cls(value=value)
        db.session.add(token)
        db.session.commit()


class Banner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    desktop = db.Column(db.Text)
    mobile = db.Column(db.Text)
    publish_time = db.Column(db.DateTime(), default=datetime.utcnow())

    def add(self):
        self.publish_time = datetime.utcnow()
        db.session.add(self)
        db.session.commit()
        return self


class SearchLog(db.Model):
    __tablename__ = 'search_log'
    id = db.Column(db.Integer, primary_key=True, unique=True)

    keyword = db.Column(db.String(255))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    module = db.Column(db.String(255))
    page = db.Column(db.Integer)
    time = db.Column(db.DateTime(), default=datetime.utcnow())

    user = db.relationship('User')

    def save(self):
        self.time = datetime.utcnow()
        db.session.add(self)
        db.session.commit()
