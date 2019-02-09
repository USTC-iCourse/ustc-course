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
            keys = [ col.strip() for col in line.split('\t') ]
            break

        for line in f:
            cols = [ col.strip() for col in line.split('\t') ]
            if len(keys) != len(cols):
                continue
            data.append(dict(zip(keys, cols)))

    return data

def parse_json(filename):
    with open(filename) as f:
        import json
        return json.load(f)

depts_code_map = dict()
classes_map = dict()
majors_map = dict()
titles_map = dict()
teachers_map = dict()
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
        teachers_map[t.name] = t
    print('%d existing teachers loaded' % len(teachers_map))

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

    int_allow_empty = lambda string: int(string) if string.strip() else 0
    course_kcbh = {}
    term = int(sys.argv[1])
    print('Term ' + str(term))
    json = parse_json(sys.argv[2])
    print('Data loaded with %d courses' % len(json['data']))
    for c in json['data']:
        course = c['course']
        code = course['code']
        course_kcbh[course['code']] = dict(
            kcid = int(course['id']),
            kcbh = course['code'],
            name = course['nameZh'],
            name_eng = course['nameEn'],
            credit = course['credits']
        )

        if 'PeriodInfo' in course:
            course_kcbh[code]['hours'] = course['PeriodInfo']['total']
            course_kcbh[code]['hours_per_week'] = course['PeriodInfo']['periodsPerWeek']

        for _t in c['teacherAssignmentList']:
            teacher = _t['teacher']
            teacher_name = teacher['person']['nameZh']
            if teacher_name in teachers_map:
                t = teachers_map[teacher_name]
            else:
                t = Teacher()
            t.name = teacher_name
            if teacher['person']['gender']['nameEn'] == 'Male':
                t.gender = 'male'
            elif teacher['person']['gender']['nameEn'] == 'Female':
                t.gender = 'female'
            else:
                t.gender = 'unknown'
            DWDM = teacher['department']['code']
            if DWDM in depts_code_map:
                t._dept = depts_code_map[DWDM]
            else:
                print('Teacher department not found ' + DWDM + ': ' + str(teacher))

            if not t.name in teachers_map:
                db.session.add(t)
                teachers_map[t.name] = t
                new_teacher_count += 1

        course_key = course['nameZh'] + '(' + ','.join(sorted([ t['teacher']['person']['nameZh'] for t in c['teacherAssignmentList'] ])) + ')'
        print('Course ' + course_key)
        if course_key in courses_map:
            course = courses_map[course_key]
        else:
            course_name = course['nameZh']
            course = Course()
            course.name = course_name
            for t in c['teacherAssignmentList']:
                course.teachers.append(teachers_map[t['teacher']['person']['nameZh']])

            db.session.add(course)
            courses_map[course_key] = course

            # course rate 
            course_rate = CourseRate()
            course_rate.course = course
            db.session.add(course_rate)
            new_course_count+=1

        # update course info
        if c['openDepartment']['code'] in depts_code_map:
            course.dept_id = depts_code_map[c['openDepartment']['code']].id
        else:
            print('Department code ' + c['openDepartment']['code'] + ' not found in ' + str(c))

        # course term
        term_key = course_key + '@' + str(term)
        print('Course term ' + term_key)
        if term_key in course_terms_map:
            course_term = course_terms_map[term_key]
        else:
            course_term = CourseTerm()
            db.session.add(course_term)
            course_terms_map[term_key] = course_term
            new_term_count+=1

        # update course term info
        course_term.course = course
        course_term.term = term
        # change 123456.01 format to the original 12345601 format
        class_code = c['code'].replace('.', '').upper()
        course_term.courseries = class_code
        course_term.class_numbers = class_code

        for key in course_kcbh[code]:
            setattr(course_term, key, course_kcbh[code][key])

        # course class
        unique_key = class_code + '@' + str(term)
        print('Course class ' + unique_key)
        if unique_key in course_classes_map:
            course_class = course_classes_map[unique_key]
            course_class.course = course # update course mapping
        else:
            course_class = CourseClass()
            db.session.add(course_class)
            course_classes_map[unique_key] = course_class
            new_class_count+=1

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

# we have merge now, do not drop existing data
db.create_all()
load_courses()
