#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import app, db
from app.utils import editor_parse_at
from app.models import *
from app.views.api import record_review_comment_history
from app.views.review import record_review_history

# require an app context to work
ctx = app.test_request_context()
ctx.push()

if sys.argv[1].isdigit():
    user = User.query.filter(User.id == sys.argv[1]).first()
else:
    user = User.query.filter(User.email == sys.argv[1]).first()
if not user:
    print('user ' + sys.argv[1] + ' not found (please use User ID or email)')
    sys.exit(1)


review_count = Review.query.filter(Review.author == user).count()
if review_count > 0:
    print(str(user) + ' has ' + str(review_count) + ' reviews')
    sys.exit(1)

comments = ReviewComment.query.filter(ReviewComment.author == user).all()
print(str(user) + ' has ' + str(len(comments)) + ' comments')

print(str(user) + ' has followed ' + str(len(user.courses_following)) + ' courses')
print(str(user) + ' has upvoted ' + str(len(user.courses_upvoted)) + ' courses')
print(str(user) + ' has downvoted ' + str(len(user.courses_downvoted)) + ' courses')
print(str(user) + ' has reviewed ' + str(len(user.reviewed_course)) + ' courses')
print(str(user) + ' has followed ' + str(len(user.users_following)) + ' users')
print(str(user) + ' has ' + str(len(user.followers)) + ' followers')
print(str(user) + ' has ' + str(len(user.notifications)) + ' notifications')
print(str(user) + ' has ' + str(len(user.upvoted_reviews)) + ' upvoted reviews')

confirm = input('Confirm to delete user ' + str(user) + '? (y/n): ')
if confirm != 'y' and confirm != 'Y':
    print('Not confirmed')
    sys.exit(1)

for comment in comments:
    record_review_comment_history(comment, 'delete')
    comment.delete()

user.courses_following = []
user.courses_upvoted = []
user.courses_downvoted = []
user.reviewed_course = []
user.users_following = []
user.followers = []
user.notifications = []
user.upvoted_reviews = []

user.is_deleted = True
user.username = None
user.email = None
user.password = ''
user.active = False
user._avatar = None
db.session.add(user)

db.session.commit()
