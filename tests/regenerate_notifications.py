#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import app
from app.utils import send_confirm_mail
from app.models import *

# require an app context to work
ctx = app.test_request_context()
ctx.push()

notifications = Notification.query.all()
for n in notifications:
    n.save()
    print(n.display_text)

#reviews = Review.query.order_by(Review.id).all()
#for review in reviews:
#    for user in set(review.course.followers + review.course.joined_users):
#        user.notify('review', review, review.author, ref_display_class='Course')
#    for user in review.upvote_users:
#        review.author.notify('upvote', review, user)
#    for comment in review.comments:
#        review.author.notify('comment', review, comment.author)
#
#
#users = User.query.all()
#for user in users:
#    for course in user.courses_upvoted:
#        for follower in course.followers:
#            follower.notify('upvote', course, user)
#    for course in user.courses_downvoted:
#        for follower in course.followers:
#            follower.notify('downvote', course, user)
#    for course in user.courses_following:
#        for follower in course.followers:
#            follower.notify('follow', course, user)
