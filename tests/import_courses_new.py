#!/usr/bin/env python3
import sys

sys.path.append('..')  # fix import directory

from app import app, db
from app.models import *
from datetime import datetime


def parse_file(filename):
  data = []
  with open(filename) as f:
    # The first line
    for line in f:
      keys = [col.strip() for col in line.split('\t')]
      break

    for line in f:
      cols = [col.strip() for col in line.split('\t')]
      if len(keys) != len(cols):
        continue
      data.append(dict(zip(keys, cols)))

  return data


def parse_json(filename):
  with open(filename, encoding='utf-8') as f:
    import json
    return json.load(f)


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
  for t in existing_teachers:
    if t.name in teachers_name_map:
      teachers_name_map[t.name].append(t)
    else:
      teachers_name_map[t.name] = [t]
    teachers_id_map[t.jwc_id] = t
  print('%d existing teachers loaded' % len(existing_teachers))

  existing_courses = Course.query.all()
  for c in existing_courses:
    courses_map[str(c)] = c
  print('%d existing courses loaded' % len(courses_map))

  existing_course_classes = CourseClass.query.all()
  for c in existing_course_classes:
    course_classes_map[str(c)] = c
  print('%d existing course classes loaded' % len(course_classes_map))

  existing_course_terms = CourseTerm.query.all()
  for c in existing_course_terms:
    course_terms_map[str(c)] = c
  print('%d existing course terms loaded' % len(course_terms_map))

  new_teacher_count = 0
  new_course_count = 0
  new_term_count = 0
  new_class_count = 0
  new_dept_count = 0

  int_allow_empty = lambda string: int(string) if string.strip() else 0
  course_kcbh = {}
  json = parse_json(sys.argv[1])
  if 'data' in json:
    json = json['data']
  print('Data loaded with %d courses' % len(json))
  for c in json:
    course = c['course']
    code = course['code']
    semester = c['semester']
    term = int(semester['code'])
    course_kcbh[code] = dict(
      kcid=int(course['id']),
      kcbh=course['code'],
      name=course['nameZh'],
      name_eng=course['nameEn'],
      credit=course['credits'],
      course_type=c['courseCategory']['nameZh'],
      course_level=c['courseGradation']['nameZh'] if c['courseGradation'] else None,
      join_type=c['classType']['nameZh'] if c['classType'] else None,
      teaching_type=c['courseType']['nameZh'] if c['courseType'] else None
    )

    if 'PeriodInfo' in course:
      course_kcbh[code]['hours'] = course['PeriodInfo']['total']
      course_kcbh[code]['hours_per_week'] = course['PeriodInfo']['periodsPerWeek']

    teachers = []
    teacher_names = []
    teacher_objects = []
    if 'teachers' in c:
      teachers = c['teachers']
    elif 'teacherAssignmentList' in c:
      teachers = c['teacherAssignmentList']
    for _t in teachers:
      if 'teacher' in _t:
        teacher = _t['teacher']
        teacher_name = teacher['person']['nameZh']
      else:
        teacher = _t
        teacher_name = teacher['nameZh']
      teacher_names.append(teacher_name)

      try:
        jwc_id = teacher['person']['id']
      except:
        jwc_id = None

      t = None
      # if jwc_id is specified, and teacher exists, use existing teacher; otherwise assume it is a new teacher
      if jwc_id is not None and jwc_id in teachers_id_map:
        t = teachers_id_map[jwc_id]
      # if jwc_id is not specified, we can only determine by teacher name
      # if there is only one teacher with the name, we assume the new course is the same teacher
      if jwc_id is None and teacher_name in teachers_name_map and len(teachers_name_map[teacher_name]) == 1:
        t = teachers_name_map[teacher_name][0]

      if t is None:  # either teacher does not exist, or name is ambiguous
        t = Teacher()
        if jwc_id is not None:
          teachers_id_map[jwc_id] = t
        if teacher_name in teachers_name_map:
          teachers_name_map[teacher_name].append(t)
        else:
          teachers_name_map[teacher_name] = [t]
        new_teacher_count += 1

      teacher_objects.append(t)

      t.name = teacher_name
      if jwc_id is not None:
        t.jwc_id = jwc_id

      try:
        if teacher['person']['gender']['nameEn'] == 'Male':
          t.gender = 'male'
        elif teacher['person']['gender']['nameEn'] == 'Female':
          t.gender = 'female'
        else:
          t.gender = 'unknown'
      except:
        t.gender = 'unknown'

      try:
        DWDM = teacher['department']['code']
        if DWDM in depts_code_map:
          t._dept = depts_code_map[DWDM]
        else:
          print('Teacher department not found ' + DWDM + ': ' + str(teacher))
      except:
        pass

      db.session.add(t)

    # deduplicate
    teacher_names = sorted(list(set(teacher_names)))
    teacher_objects = list(set(teacher_objects))

    course_key = course['nameZh'] + '(' + ','.join(teacher_names) + ')'
    course_code_short = course['code']
    if course_key in courses_map:
      course = courses_map[course_key]
      course.teachers = teacher_objects
      db.session.add(course)
      # print('Existing course ' + course_key)
    else:
      course_name = course['nameZh']
      course = Course()
      course.name = course_name
      course.teachers = teacher_objects
      db.session.add(course)

      courses_map[course_key] = course

      # course rate
      course_rate = CourseRate()
      course_rate.course = course
      db.session.add(course_rate)
      print('New course ' + course_key)
      new_course_count += 1

    # update course info
    if c['openDepartment']['code'] in depts_code_map:
      course.dept_id = depts_code_map[c['openDepartment']['code']].id
    else:
      dept = Dept()
      dept.code = c['openDepartment']['code']
      dept.name = c['openDepartment']['simpleNameZh']
      dept.name_eng = c['openDepartment']['nameEn']
      db.session.add(dept)
      print('New department ' + dept.name)
      new_dept_count += 1

    # course term
    term_key = course_key + '@' + str(term)
    if term_key in course_terms_map:
      course_term = course_terms_map[term_key]
      # print('Existing course term ' + term_key)
    else:
      course_term = CourseTerm()
      db.session.add(course_term)
      course_terms_map[term_key] = course_term
      print('New course term ' + term_key)
      new_term_count += 1

    # update course term info
    course_term.course = course
    course_term.term = term
    # change 123456.01 format to the original 12345601 format
    class_code = c['code'].replace('.', '').upper()
    course_term.courseries = class_code
    course_term.code = course_code_short
    course_term.class_numbers = class_code

    for key in course_kcbh[code]:
      setattr(course_term, key, course_kcbh[code][key])

    # course class
    unique_key = class_code + '@' + str(term)
    if unique_key in course_classes_map:
      course_class = course_classes_map[unique_key]
      course_class.course = course  # update course mapping
      # print('Existing course class ' + unique_key)
    else:
      course_class = CourseClass()
      db.session.add(course_class)
      course_classes_map[unique_key] = course_class
      print('New course class ' + unique_key)
      new_class_count += 1

    # update course class info
    course_class.course = course
    course_class.term = term
    course_class.cno = class_code

  print('load complete, committing changes to database')
  db.session.commit()
  print('%d new teachers loaded' % new_teacher_count)
  print('%d new courses loaded' % new_course_count)
  print('%d new terms loaded' % new_term_count)
  print('%d new classes loaded' % new_class_count)
  print('%d new departments loaded' % new_dept_count)


# we have merge now, do not drop existing data
db.create_all()
load_courses()
