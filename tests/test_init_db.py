#!/usr/bin/env python3
# Test database creation and basic data insertion

# A SQLite database will be created at /tmp/test.db
# If you want to clear the database, just delete /tmp/test.db

import sys
sys.path.append('..')  # fix import directory

from app import app,db,user_datastore
from app.models import Student,Course
from random import randint

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////tmp/test.db'


db.create_all()
for i in range(1, 10):
    stu = Student('PB10' + str(randint(100000, 999999)), '李博杰', '11')
    course = Course('test'+str(randint(100000,999999)),'线性代数','test')
    db.session.add(course)
    db.session.add(stu)
db.session.commit()

user_datastore.create_user(email='test@163.com',password='password')
db.session.commit()

print(Student.query.all())
print()
print(Student.query.filter_by(dept='11').first())
print(Course.query.all())
