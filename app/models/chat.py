from app import db
from datetime import datetime

class Conversation(db.Model):
    __tablename__ = 'conversations'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    first_query = db.Column(db.Text, nullable=True)

    messages = db.relationship('ChatMessage', back_populates='conversation', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Conversation {self.id}>'

class ChatMessage(db.Model):
    __tablename__ = 'chat_messages'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversations.id'), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    intent_analysis = db.Column(db.Text)
    search_results = db.Column(db.Text)
    ai_response = db.Column(db.Text)
    timing_stats = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    conversation = db.relationship('Conversation', back_populates='messages')

    def __repr__(self):
        return f'<ChatMessage {self.id}>'
