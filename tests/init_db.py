#!/usr/bin/env python3
# Test database creation and basic data insertion

# A SQLite database will be created at /tmp/test.db
# If you want to clear the database, just delete /tmp/test.db

import sys
sys.path.append('..')  # fix import directory

from model import db, Student
from random import randint

db.create_all()
for i in range(1, 10):
    stu = Student('PB10' + str(randint(100000, 999999)), '李博杰', '11')
    db.session.add(stu)
db.session.commit()

print(Student.query.all())
print(Student.query.filter_by(dept='11').first())
