#!/usr/bin/env python3
# Test database creation and basic data insertion

# A SQLite database will be created at /tmp/test.db
# If you want to clear the database, just delete /tmp/test.db

import sys
sys.path.append('..')  # fix import directory

from app import app,db
from app.models import *
from random import randint

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'


db.create_all()
for i in range(1, 10):
    Student.create(sno='PB10' + str(randint(100000, 999999)), name='李博杰', dept= '11')
    course = Course.create(cno='test'+str(randint(100000,999999)),term='20142',name='线性代数',dept='test')
    print(course)

CourseReview.create(author_id=1, course_id=1, rate=4, upvote=2, content='Hello World')
CourseReview.create(author_id=2, course_id=1, rate=4, upvote=2, content='Hello World1')
CourseReview.create(author_id=3, course_id=1, rate=4, upvote=2, content='Hello World2')
CourseReview.create(author_id=4, course_id=1, rate=4, upvote=2, content='Hello World3')
CourseReview.create(author_id=5, course_id=1, rate=4, upvote=2, content='Hello World4')
CourseReview.create(author_id=6, course_id=1, rate=4, upvote=2, content='Hello World5')

try:
    uuser_datastore.create_user(email='test@163.com',password='password')
except:
    pass

print(Student.query.all())
print()
print(Student.query.filter_by(dept='11').first())
print(Course.query.all())
