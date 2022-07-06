#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import app, db
from app.utils import editor_parse_at
from app.models import Review, ReviewComment
from app.views.api import record_review_comment_history
from app.views.review import record_review_history

# require an app context to work
ctx = app.test_request_context()
ctx.push()

reviews = Review.query.all()
for review in reviews:
    content, mentioned_users = editor_parse_at(review.content)
    if len(mentioned_users) > 0:
        print(review, mentioned_users)

        review.content = content
        db.session.add(review)
        record_review_history(review, 'fix_at')
        for user in mentioned_users:
            user.notify('mention', review, review.author)

review_comments = ReviewComment.query.all()
for comment in review_comments:
    content, mentioned_users = editor_parse_at(comment.content)
    if len(mentioned_users) > 0:
        print(comment, mentioned_users)

        comment.content = content
        db.session.add(comment)
        record_review_comment_history(comment, 'fix_at')
        for user in mentioned_users:
            user.notify('mention', comment, comment.author)

db.session.commit()
