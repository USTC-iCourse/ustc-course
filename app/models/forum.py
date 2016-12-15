from datetime import datetime
from app import db
try:
    from flask_login import current_user
except:
    current_user=None

forum_thread_upvotes = db.Table('forum_thread_upvotes',
    db.Column('thread_id', db.Integer, db.ForeignKey('forum_threads.id'), primary_key=True),
    db.Column('author_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

class ForumThread(db.Model):
    __tablename__ = 'forum_threads'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'))

    upvote = db.Column(db.Integer,default=0) #点赞数量
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    publish_time = db.Column(db.DateTime, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, default=datetime.utcnow)

    post_count = db.Column(db.Integer, default=0)
    upvote_count = db.Column(db.Integer, default=0)

    author = db.relationship('User', backref='forum_threads')
    #:course: backref to Course
    posts = db.relationship('ForumPost',backref='thread')
    upvotes = db.relationship('User', secondary=forum_thread_upvotes)

    def save(self, course, title, content, author=current_user):
        if course and author:
            self.course = course
            self.author = author
            self.title = title
            self.content = content
            db.session.add(self)
            db.session.commit()


forum_post_upvotes = db.Table('forum_post_upvotes',
    db.Column('post_id', db.Integer, db.ForeignKey('forum_posts.id'), primary_key=True),
    db.Column('author_id', db.Integer, db.ForeignKey('users.id'), primary_key=True)
)

class ForumPost(db.Model):
    __tablename__ = 'forum_posts'

    id = db.Column(db.Integer, primary_key=True, unique=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    thread_id = db.Column(db.Integer, db.ForeignKey('forum_threads.id'))

    upvote = db.Column(db.Integer,default=0) #点赞数量
    content = db.Column(db.Text)
    publish_time = db.Column(db.DateTime, default=datetime.utcnow)
    update_time = db.Column(db.DateTime, default=datetime.utcnow)

    upvote_count = db.Column(db.Integer, default=0)

    author = db.relationship('User', backref='forum_posts')
    #:thread: backref to ForumThread
    upvotes = db.relationship('User', secondary=forum_post_upvotes)

    def save(self, thread, content, author=current_user):
        if thread and author:
            self.thread = thread
            self.author = author
            self.content = content
            db.session.add(self)
            db.session.commit()

