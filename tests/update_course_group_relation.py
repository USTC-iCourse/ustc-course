#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import app, db
from app.models import *

course_terms = CourseTerm.query.all()
course_groups = CourseGroup.query.all()
course_group_map = { course_group.code : course_group for course_group in course_groups }

for course_term in course_terms:
    if course_term.code in course_group_map:
        course_term.course.course_groups += [course_group_map[course_term.code]]

db.session.commit()
