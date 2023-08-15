#!/usr/bin/python3
import sys

sys.path.append('..')
import os
from app.models import Review
import pdftotext
import re


def find_reviews_in_text(text):
  urls = re.findall('/course/[0-9]+/#review-[0-9]+', text)
  review_ids = []
  for url in urls:
    match = re.match('/course/[0-9]+/#review-([0-9]+)', url)
    review_ids.append(int(match.group(1)))
  return review_ids


def find_anonymous_reviews(review_ids):
  anonymous_reviews = []
  for review_id in review_ids:
    review = Review.query.get(review_id)
    if review and review.is_anonymous:
      anonymous_reviews.append(review_id)
      print('Found anonymous review ', review, review.course, review.author)
  return anonymous_reviews


base_folder = '../uploads/rankings-history'
for filename in os.listdir(base_folder):
  if filename.endswith('.pdf'):
    with open(os.path.join(base_folder, filename), "rb") as f:
      pdf = pdftotext.PDF(f)
      reviews = find_reviews_in_text("\n".join(pdf))
      anonymous_reviews = find_anonymous_reviews(reviews)
      print(filename, anonymous_reviews)
