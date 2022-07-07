#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import app, db
from app.models import Course

# require an app context to work
ctx = app.test_request_context()
ctx.push()

courses = Course.query.all()
for course in courses:
    course.update_rate(commit_db=False)

db.session.commit()
