#!/usr/bin/python3
import sys
sys.path.append('..')
from app import app, db
from app.models import Review
from lxml.html.clean import Cleaner
from app.utils import sanitize
from app.views.review import record_review_history

with app.app_context():
    reviews = Review.query.all()
    print(len(reviews))

    for review in reviews:
        print(review.id)
        new_content = sanitize(review.content)
        if new_content != review.content:
            print('=======')
            print(review.content)
            print('-------')
            print(new_content)
            print('=======')
            review.content = new_content
            db.session.add(review)
            db.session.commit()

            record_review_history(review, 'clean-html')
            db.session.commit()
