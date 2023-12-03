#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import app, db
from app.models import *
from datetime import datetime
import json
import requests
import subprocess

# configuration for information source
domain = 'catalog.ustc.edu.cn'
site_root = 'https://' + domain + '/'

headers = {
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
    'authority': domain,
    'referer': site_root + 'plan'
}

# get access token
token_json = requests.get(site_root + 'get_token', headers=headers)
access_token = json.loads(token_json.text)['access_token']

# load existing data
with app.app_context():
    existing_majors = Major.query.all()
    majors_map = { major.code : major for major in existing_majors }

    existing_programs = Program.query.all()
    programs_map = { program.id : program for program in existing_programs }

    existing_course_groups = CourseGroup.query.all()
    course_groups_map = { course_group.code : course_group for course_group in existing_course_groups }

    existing_program_courses = ProgramCourse.query.all()
    program_courses_map = { str(program_course.program_id) + '|' + str(program_course.course_group_code) : program_course for program_course in existing_program_courses }

    existing_depts = Dept.query.all()
    depts_map = { dept.code : dept for dept in existing_depts }


def load_course_group(course):
    course_group = course_groups_map[course['code']] if course['code'] in course_groups_map else CourseGroup()

    course_group.code = course['code']
    course_group.course_gradation = course['courseGradation']
    course_group.credits = course['credits']
    course_group.introduction = course['introduction']
    course_group.name = course['nameZh']
    course_group.name_en = course['nameEn']
    course_group.seasons = course['seasons']
    course_group.total_periods = course['totalPeriods']

    course_groups_map[course_group.code] = course_group
    db.session.add(course_group)
    return course_group


def load_dept(dept_data):
    dept = depts_map[dept_data['code']] if dept_data['code'] in depts_map else Dept()

    dept.code = dept_data['code']
    dept.name = dept_data['nameZh']

    depts_map[dept.code] = dept
    db.session.add(dept)
    return dept


def to_numeric_term(term_str):
    term_str.replace('0--', '9')  # 毕业论文用 0-- 代替，应该是排在最后的
    return term_str.replace('春', '1').replace('秋', '0').replace('夏', '2')


def load_program_course(program_id, course_type, course):
    course_group = course_groups_map[course['course']['code']]
    key = str(program_id) + '|' + str(course_group.code)
    program_course = program_courses_map[key] if key in program_courses_map else ProgramCourse()

    program_course.program_id = program_id
    program_course.course_group_code = course_group.code
    program_course.dept_id = load_dept(course['department']).id
    program_course.compulsory = course['compulsory']
    program_course.exam_mode = course['examMode']
    program_course.total_periods = course['totalPeriods']
    program_course.weeks = course['weeks']
    program_course.type = course_type
    program_course.remark = course['remark']
    program_course.terms = ','.join(course['terms'])
    program_course.terms_numeric = to_numeric_term(program_course.terms)

    program_courses_map[key] = program_course
    db.session.add(program_course)
    return program_course


def load_program_recursive(program_id, tree):
    count = 0
    if isinstance(tree, list):
        for item in tree:
            count += load_program_recursive(program_id, item)
    elif isinstance(tree, dict):
        if 'isLeaf' in tree and tree['isLeaf']:
            courses = tree['self']['courses']
            course_type = tree['self']['type']
            for course in courses:
                load_course_group(course['course'])
                load_program_course(program_id, course_type, course)
                count += 1
        else:
            for key in tree:
                count += load_program_recursive(program_id, tree[key])
    return count


def load_program(program_id):
    url = site_root + 'api/teach/program/info/' + str(program_id)
    param = 'access_token=' + access_token
    tree_json = requests.get(url + '?' + param, headers=headers)
    tree = json.loads(tree_json.text)
    module_tree = tree['moduleTree']
    return load_program_recursive(program_id, module_tree)


def load_tree():
    tree_json = requests.get(site_root + 'api/teach/program/tree?access_token=' + access_token, headers=headers)
    tree = json.loads(tree_json.text)
    
    for json_dept_id in tree:
        dept_data = tree[json_dept_id]
        dept_code = dept_data['code']
        dept_name = dept_data['nameZh']
        dept = load_dept(dept_data)

        for major_id in dept_data['majors']:
            major_data = dept_data['majors'][major_id]
            major_code = major_data['code']
    
            major = majors_map[major_code] if major_code in majors_map else Major()
            major.code = major_code
            major.name = major_data['nameZh']
            major.name_en = major_data['nameEn']
            majors_map[major.code] = major
            db.session.add(major)
    
            programs = major_data['programs']
            for program_data in programs:
                program_id = program_data['id']
                program = programs_map[program_id] if program_id in programs_map else Program()
                program.id = program_id
                program.dept_id = dept.id
                program.major_id = major.id
                program.name = program_data['nameZh']
                program.name_en = program_data['nameEn']
                program.grade = program_data['grade']
                program.train_type = program_data['trainType']
                programs_map[program.id] = program
                db.session.add(program)

                count = load_program(program_id)
                db.session.commit()

                print('Loaded ' + str(count) + ' courses in ' + program.train_type + ' ' + dept_name + ' ' + major.name + ' ' + str(program.grade) + ' ' + program.name)

with app.app_context():
    load_tree()

subprocess.run(['python3', 'update_course_group_relation.py'])
print('Updated course group relations')
