#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import app, db
from app.models import Teacher

ctx = app.test_request_context()
ctx.push()

def dedup_teacher(teacher_id):
    teachers = Teacher.query.filter(Teacher.id==teacher_id).all()
    if len(teachers) == 0:
        print('No such teacher ID ' + str(teacher_id))
        return
    
    teacher = teachers[0]
    if teacher.user_id:
        print('Teacher is already registered, cannot dedup')
        return
    courses = teacher.courses.all()
    for course in courses:
        print(str(course.id) + ' ' + str(course))
    print('Please assign courses to different teachers, and mark with different labels:')
    labeled_courses = {}
    for course in courses:
        label = input(str(course.id) + ' ' + str(course) + ': ')
        if label in labeled_courses:
            labeled_courses[label].append(course)
        else:
            labeled_courses[label] = [course]
    print(labeled_courses)
    confirm = input('Confirm? (y/n): ')
    if confirm != 'y' and confirm != 'Y':
        print('Not confirmed, discard changes')
        return
    if len(labeled_courses) == 1:
        print('Only one course, nothing to do')
        return
    index = 0
    for label in labeled_courses:
        index += 1
        if index == 1:
            continue

        new_teacher = Teacher()
        new_teacher.name = teacher.name
        new_teacher.dept_id = teacher.dept_id
        new_teacher.email = teacher.email
        new_teacher.title = teacher.title
        new_teacher.office_phone = teacher.office_phone
        new_teacher.gender = teacher.gender
        new_teacher.description = teacher.description
        new_teacher.homepage = teacher.homepage
        new_teacher.research_interest = teacher.research_interest
        new_teacher._image = teacher._image
        new_teacher.last_edit_time = teacher.last_edit_time
        new_teacher.image_locked = teacher.image_locked
        new_teacher.info_locked = teacher.info_locked
        new_teacher.access_count = teacher.access_count
        db.session.add(new_teacher)

        for course in labeled_courses[label]:
            course_teachers = []
            for t in course.teachers:
                course_teachers.append(new_teacher if t == teacher else t)
            course.teachers = course_teachers
            db.session.add(course)

    db.session.commit()
    print('Teacher information saved')

dedup_teacher(int(sys.argv[1]))
