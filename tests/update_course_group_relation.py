#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import app, db
from app.models import *


def is_in_group(course_term, course_group):
    for group in course_term.course.course_groups:
        if group == course_group:
            return True
    return False

rows = []

with app.app_context():
    course_terms = CourseTerm.query.all()
    course_groups = CourseGroup.query.all()
    course_group_map = { course_group.code : course_group for course_group in course_groups }

    for course_term in course_terms:
        if course_term.code in course_group_map:
            course_group = course_group_map[course_term.code]
            if not is_in_group(course_term, course_group):
                #print('code=', course_group.code, 'term=', course_term, 'course=', course_term.course)
                rows.append({ 'code': course_group.code, 'course_id': course_term.course.id })

    stmt = course_group_relation.insert().values(rows)
    db.session.execute(stmt)
    db.session.commit()
