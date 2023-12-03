
#!/usr/bin/python3
import sys
sys.path.append('..')
from app import app, db
from app.models import Review, ReviewComment
from app.views.review import record_review_history
from app.views.api import record_review_comment_history

def update_reviews():
    reviews = Review.query.all()
    for review in reviews:
        operation = 'create' if review.publish_time == review.update_time else 'update'
        history = record_review_history(review, operation, commit=False)
        history.operation_time = review.update_time
        history.operation_user_id = review.author_id
        db.session.add(history)

    db.session.commit()


def update_comments():
    comments = ReviewComment.query.all()
    for comment in comments:
        operation = 'create'
        history = record_review_comment_history(comment, operation, commit=False)
        history.operation_time = comment.publish_time
        history.operation_user_id = comment.author_id
        db.session.add(history)

    db.session.commit()


with app.app_context():
    update_reviews()
    update_comments()
