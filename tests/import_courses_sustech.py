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
    json = parse_json(sys.argv[1])
    if 'data' in json:
        json = json['data']
    print('Data loaded with %d courses' % len(json))
    for c in json:
        # course = c['course'] #name str data
        code = c['kcdm']  # CS001
        semester = "2021-2022"  # manual add?
        # https://github.com/jingning42/ustc-course/blob/66c68a9615d4f658c51d5273b7869d02ee5ddd3d/app/models/course.py#L85
        term = '20211'  # manual add
        course_kcbh[code] = dict(
            # kcid=c['kcid'],  #"2FCC66B429FA494A8F902D739570FCC3" #需要做个hash
            kcid=abs(hash(c['kcid'])) % (10 ** 8),  # "55932488" #需要做个hash
            kcbh=c['kcdm'],  # "CS102A",
            name=c['kcmc'],  # "计算机程序设计基础A",
            name_eng=c['kcmc_en'],
            credit=c['xf'],
            course_type=c['kclbmc'] if c['kclbmc'] else None,  # '专业基础课'
            course_level=c['pyccmc'] if c['pyccmc'] else None,  # '本科'
            # join_type=c['classType']['nameZh'] if c['classType'] else None,
            join_type=c['rwlxmc'] if c['rwlxmc'] else None,
            course_major=c['kkyxmc'],  # 'xx系'
            # teaching_type=c['skfs'] if c['skfs'] else None #"理论+实践"
            teaching_type=c['skyymc']  # '英文'
        )

        if c['zxs']:
            course_kcbh[code]['hours'] = int(float(c['zxs']))
            course_kcbh[code]['hours_per_week'] = int(float(c['zxs']) / 16)

        # teachers
        teachers = []
        teacher_names = []
        if 'dgjsmc' in c:
            teachers = c['dgjsmc']
            teachers = list(set(teachers.split(','))) if teachers else [
                '未知教师']  # in case of null and dup like '"dgjsmc": "刘欢,刘欢",'
        # elif 'teacherAssignmentList' in c:
        #     teachers = c['teacherAssignmentList']
        for _t in teachers:
            # teacher = _t['teacher']
            teacher_name = _t
            # else:
            #     teacher = _t
            #     teacher_name = teacher['nameZh']
            teacher_names.append(teacher_name)
            if teacher_name in teachers_map:
                t = teachers_map[teacher_name]
            else:
                t = Teacher()
            t.name = teacher_name
            t.gender = 'unknown'
            # try:
            #     if teacher['person']['gender']['nameEn'] == 'Male':
            #         t.gender = 'male'
            #     elif teacher['person']['gender']['nameEn'] == 'Female':
            #         t.gender = 'female'
            #     else:
            #         t.gender = 'unknown'
            # except:
            #     t.gender = 'unknown'

            # try:
            #     DWDM = teacher['department']['code']
            #     if DWDM in depts_code_map:
            #         t._dept = depts_code_map[DWDM]
            #     else:
            #         print('Teacher department not found ' + DWDM + ': ' + str(teacher))
            # except:
            #     pass

            if not t.name in teachers_map:
                db.session.add(t)
                teachers_map[t.name] = t
                new_teacher_count += 1

        course_key = c['kcmc'] + '(' + ','.join(sorted(teacher_names)) + ')'
        if course_key in courses_map:
            course = courses_map[course_key]
            print('Existing course ' + course_key)
        else:
            course_name = c['kcmc']
            course = Course()
            course.name = course_name
            course.teachers = []
            db.session.add(course)

            for t in teacher_names:
                course.teachers.append(teachers_map[t])

            db.session.add(course)
            courses_map[course_key] = course

            # course rate
            course_rate = CourseRate()
            course_rate.course = course
            db.session.add(course_rate)
            print('New course ' + course_key)
            new_course_count += 1

        # update course info
        depts_hash = c['kkyx']
        depts_text = c['kkyxmc']
        # depts_text = 37
        if depts_hash in depts_code_map:
            course.dept_id = depts_code_map[depts_text].id
        else:
            print('Department code' + c['kkyxmc'] + str(depts_hash) + ' not found in ' + str(c['kcdm']))

        # course term
        # https://github.com/jingning42/ustc-course/blob/66c68a9615d4f658c51d5273b7869d02ee5ddd3d/app/utils.py#L217
        term_key = course_key + '@' + str(term)
        if term_key in course_terms_map:
            course_term = course_terms_map[term_key]
            print('Existing course term ' + term_key)
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
        class_code = c['kcdm'].replace('.', '').upper()
        course_term.courseries = class_code
        course_term.class_numbers = class_code

        for key in course_kcbh[code]:
            setattr(course_term, key, course_kcbh[code][key])

        # course class
        unique_key = class_code + '@' + str(term)
        if unique_key in course_classes_map:
            course_class = course_classes_map[unique_key]
            course_class.course = course  # update course mapping
            print('Existing course class ' + unique_key)
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


#
# sqlalchemy.exc.DataError: (MySQLdb._exceptions.DataError) (1265, "Data truncated for column 'kcid' at row 1")
# [SQL: INSERT INTO course_terms (course_id, term, courseries, kcid, course_major, course_type, course_level, join_type, teaching_type, grading_type, teaching_material, reference_material, student_requirements, description, description_eng, credit, hours, hours_per_week, class_numbers, campus, start_week, end_week) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)]
# [parameters: (1, '2021-22-SP', 'CS102A', '2FCC66B429FA494A8F902D739570FCC3', None, '通识必修课', '本', None, '理论+实践', None, None, None, None, None, None, 3, '64', 4.0, 'CS102A', None, None, None)]
# (Background on this error at: https://sqlalche.me/e/14/9h9h)

# sqlalchemy.exc.DataError: (MySQLdb._exceptions.DataError) (1265, "Data truncated for column 'kcid' at row 1")
# [SQL: INSERT INTO course_terms (course_id, term, courseries, kcid, course_major, course_type, course_level, join_type, teaching_type, grading_type, teaching_material, reference_material, student_requirements, description, description_eng, credit, hours, hours_per_week, class_numbers, campus, start_week, end_week) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)]
# [parameters: (1, '20211', 'BIO222', '56294118ascxascs', '生物系', '专业任务', '专业基础课', None, None, None, None, None, None, None, None, '2.0', 64, 4, 'BIO222', None, None, None)]


# we have merge now, do not drop existing data
db.create_all()
load_courses()
