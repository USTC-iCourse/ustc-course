#!/usr/bin/python3
import sys
sys.path.append('..')
from app import db
from app.models import Review
from lxml.html.clean import Cleaner

review = Review.query.order_by(Review.id).first()
while review is not None:
	print(review.id)
	cleaner = Cleaner(safe_attrs_only=False, style=False)
	new_content = cleaner.clean_html(review.content)
	if new_content != review.content:
		print('=======')
		print(review.content)
		print('-------')
		print(new_content)
		print('=======')
		review.content = new_content
		db.session.commit()

	review = Review.query.filter(Review.id > review.id).order_by(Review.id).first()
