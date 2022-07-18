#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import app, db
from app.models import Course, Review

# require an app context to work
ctx = app.test_request_context()
ctx.push()

print('Loading courses...')
courses = Course.query.all()
print('Fixing course rates...')
for course in courses:
    course.update_rate(commit_db=False)
    course.course_rate.upvote_count = len(course.upvote_users)
    course.course_rate.downvote_count = len(course.downvote_users)

db.session.commit()

print('Loading reviews...')
reviews = Review.query.all()
print('Fixing review upvotes...')
for review in reviews:
    review.upvote_count = len(review.upvote_users)
    review.comment_count = len(review.comments)

db.session.commit()
