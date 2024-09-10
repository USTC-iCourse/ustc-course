from app import db
from datetime import datetime

class ChatHistory(db.Model):
    __tablename__ = 'chat_histories'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    session_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    first_query = db.Column(db.Text, nullable=True)

    messages = db.relationship('ChatMessage', backref='chat_history', lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<ChatHistory {self.id}>'

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'

    id = db.Column(db.Integer, primary_key=True)
    chat_history_id = db.Column(db.Integer, db.ForeignKey('chat_histories.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    context = db.Column(db.Text, nullable=True)
    search_time = db.Column(db.Float, nullable=True)
    time_to_first_token = db.Column(db.Float, nullable=True)
    total_response_time = db.Column(db.Float, nullable=True)
    search_results = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<ChatMessage {self.id}>'
