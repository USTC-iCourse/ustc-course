from app import db
from datetime import datetime, timedelta
import secrets


class SearchToken(db.Model):
    """One-time token for search API to prevent DoS attacks"""
    __tablename__ = 'search_tokens'
    
    token = db.Column(db.String(64), primary_key=True)
    created_at = db.Column(db.DateTime(), default=datetime.utcnow, nullable=False)
    used = db.Column(db.Boolean(), default=False, nullable=False)
    ip_address = db.Column(db.String(45))  # Support IPv6
    
    @classmethod
    def generate(cls, ip_address=None):
        """Generate a new one-time search token"""
        token = secrets.token_urlsafe(32)
        search_token = cls(token=token, ip_address=ip_address)
        db.session.add(search_token)
        db.session.commit()
        return token
    
    @classmethod
    def validate_and_use(cls, token):
        """Validate and mark token as used. Returns True if valid, False otherwise."""
        if not token:
            return False
            
        search_token = cls.query.filter_by(token=token).first()
        if not search_token:
            return False
        
        # Check if already used
        if search_token.used:
            return False
        
        # Check if expired (tokens expire after 5 minutes)
        if datetime.utcnow() - search_token.created_at > timedelta(minutes=5):
            # Clean up expired token
            db.session.delete(search_token)
            db.session.commit()
            return False
        
        # Mark as used
        search_token.used = True
        db.session.commit()
        return True
    
    @classmethod
    def cleanup_old_tokens(cls):
        """Remove tokens older than 1 hour"""
        cutoff_time = datetime.utcnow() - timedelta(hours=1)
        cls.query.filter(cls.created_at < cutoff_time).delete()
        db.session.commit()


class RevokedToken(db.Model):
    value = db.Column(db.String(100), unique=True, primary_key=True)
    revoke_time = db.Column(db.DateTime(), default=datetime.utcnow())

    @classmethod
    def add(cls, value):
        token = cls(value=value)
        db.session.add(token)
        db.session.commit()


class PasswordResetToken(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    token = db.Column(db.String(255), unique=True, nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)

    def is_expired(self):
        return datetime.utcnow() > self.expires_at


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


class Announcement(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    last_editor_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.Text)
    content = db.Column(db.Text)
    publish_time = db.Column(db.DateTime(), default=datetime.utcnow())
    update_time = db.Column(db.DateTime(), default=datetime.utcnow())

    author = db.relationship('User', foreign_keys=[author_id])
    last_editor = db.relationship('User', foreign_keys=[last_editor_id])

    def add(self):
        self.publish_time = datetime.utcnow()
        self.update_time = self.publish_time
        db.session.add(self)
        db.session.commit()

    def save(self):
        self.update_time = datetime.utcnow()
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()
