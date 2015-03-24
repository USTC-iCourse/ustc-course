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
