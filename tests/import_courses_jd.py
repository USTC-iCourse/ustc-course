#!/usr/bin/env python3
import sys
import uuid

sys.path.append('..')  # fix import directory

from app import app, db
from app.models import *
from datetime import datetime
import pickle

import dataclasses

import dataclasses
import pickle
from pathlib import Path
import pandas as pd


@dataclasses.dataclass
class JDCourse:
  name: str
  id: str
  semester: str
  recommendation: str
  reviews: list
  optional_course_is_core: bool
  highest: float
  average: float
  lowest: float
  df_course: pd.DataFrame
  class_headcount: int


jd = pickle.load(open('/tmp/courses.pickle', 'rb'))


depts_code_map = dict()
classes_map = dict()
majors_map = dict()
titles_map = dict()
teachers_id_map = dict()
teachers_name_map = dict()
# We should load all existing courses, because SQLAlchemy does not support .merge on non-primary-key,
# and we want to preserve course ID (primary key) for each (cno, term) pair.
course_classes_map = dict()
course_terms_map = dict()
courses_map = dict()


def load_courses(insert=True):
  existing_depts = Dept.query.all()
  for dept in existing_depts:
    depts_code_map[dept.code] = dept
  print('%d existing departments loaded' % len(depts_code_map))

  existing_teachers = Teacher.query.all()
  print('%d existing teachers loaded' % len(existing_teachers))

  existing_courses = Course.query.all()
  print('%d existing courses loaded' % len(existing_courses))

  existing_course_classes = CourseClass.query.all()
  print('%d existing course classes loaded' % len(existing_course_classes))

  existing_course_terms = CourseTerm.query.all()
  print('%d existing course terms loaded' % len(existing_course_terms))

  new_teacher_count = 0
  new_course_count = 0
  new_term_count = 0
  new_class_count = 0
  new_dept_count = 0

  int_allow_empty = lambda string: int(string) if string.strip() else 0
  course_kcbh = {}

  print('Data loaded with %d courses' % len(jd))

  user =  User.query.filter_by(username='initbot1').first()
  if user is None:
    user = User(username='initbot1', email='initbot@xjtumen.nonexists', password=str(uuid.uuid4().hex))
    user.xjtumen_username = 'course_init_bot'

    user.role = 'Bot'
    user.save()
    user.confirm()

  for c_name, c_list in jd.items():
    c = c_list[0]
    t = Teacher()

    t.name = '未名教师'
    t.gender = 'unknown'

    db.session.add(t)

    course = Course()
    course.name = c_name
    # course.id = c.id
    db.session.add(course)
    course.teachers = [t]
    course_rate = CourseRate()
    course_rate.course = course
    db.session.add(course_rate)

    if len(c_list) == 1 and c.semester == '20771':
      course_term = CourseTerm()
      db.session.add(course_term)
      course_term.course = course
      course_term.term = '20772'
      course_term.courseries = c.id
      course_term.code = c.id
    for c in c_list:
      course_term = CourseTerm()
      db.session.add(course_term)
      course_term.course_type = '核心选修' if c.optional_course_is_core else '其他选修'
      if c.highest is not None:
        course_term.grade_highest = c.highest
        course_term.grade_lowest = c.lowest
        course_term.grade_average = c.average

      course_term.course = course
      course_term.term = c.semester
      if c.df_course is not None:
        course_term.has_grade_graph = True
        course_term.grade_u60 = c.grade_range_student_count[0]
        course_term.grade_61_70 = c.grade_range_student_count[1]
        course_term.grade_71_80 = c.grade_range_student_count[2]
        course_term.grade_81_90 = c.grade_range_student_count[3]
        course_term.grade_91_100 = c.grade_range_student_count[4]
      else:
        course_term.has_grade_graph = False
      course_term.courseries = c.id
      course_term.code = c.id
      # course_term.class_numbers = '2'

      course_class = CourseClass()
      # update course class info
      course_class.course = course
      course_class.term = c.semester

      # course_class.cno = '1'
      db.session.add(course_class)

      once = False
      for review_content in c.reviews:
        review = Review()
        db.session.add(review)
        review.course = course

        review.term = c.semester
        review.difficulty = 2
        review.homework = 2
        review.grading = 2
        review.gain = 2
        review.rate = 5
        review.author = user
        review.content = review_content
        if once:
          if c.recommendation is not None:
            review.content = f'{c.recommendation}\n{review.content}'
        review.update_time = datetime.utcnow()

        history = ReviewHistory()
        db.session.add(history)

        history.difficulty = review.difficulty
        history.homework = review.homework
        history.grading = review.grading
        history.gain = review.gain
        history.rate = review.rate
        history.content = review.content
        history.author_id = review.author_id
        history.course_id = review.course_id
        history.term = review.term
        history.publish_time = review.publish_time
        history.update_time = review.update_time
        history.is_anonymous = review.is_anonymous
        history.only_visible_to_student = review.only_visible_to_student
        history.is_hidden = review.is_hidden
        history.is_blocked = review.is_blocked

        history.review_id = review.id
        history.operation = 'create'
        history.operation_user_id = user.id

  db.session.commit()


with app.app_context():
  # we have merge now, do not drop existing data
  db.create_all()
  load_courses()
