#!/usr/bin/env python3
# modified from import_courses_new.py
from pathlib import Path
import sys

sys.path.append("..")  # fix import directory

from app import app, db
from app.models import *
from datetime import datetime
import argparse


def parse_file(filename):
    data = []
    with open(filename) as f:
        # The first line
        for line in f:
            keys = [col.strip() for col in line.split("\t")]
            break

        for line in f:
            cols = [col.strip() for col in line.split("\t")]
            if len(keys) != len(cols):
                continue
            data.append(dict(zip(keys, cols)))

    return data


def parse_json(filename):
    with open(filename, encoding="utf-8") as f:
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


def load_courses(args):
    existing_depts = Dept.query.all()
    for dept in existing_depts:
        depts_code_map[dept.code] = dept
    print("%d existing departments loaded" % len(depts_code_map))

    existing_teachers = Teacher.query.all()
    for t in existing_teachers:
        teachers_map[t.name] = t
    print("%d existing teachers loaded" % len(teachers_map))

    existing_courses = Course.query.all()
    for c in existing_courses:
        courses_map[str(c)] = c
    print("%d existing courses loaded" % len(courses_map))

    existing_course_classes = CourseClass.query.all()
    for c in existing_course_classes:
        course_classes_map[str(c)] = c
    print("%d existing course classes loaded" % len(course_classes_map))

    existing_course_terms = CourseTerm.query.all()
    for c in existing_course_terms:
        course_terms_map[str(c)] = c
    print("%d existing course terms loaded" % len(course_terms_map))

    new_teacher_count = 0
    new_course_count = 0
    new_term_count = 0
    new_class_count = 0

    int_allow_empty = lambda string: int(string) if string.strip() else 0
    course_kcbh = {}
    lesson_json = parse_json(args.lesson)
    semester_json = parse_json(args.semester)
    semester_id = args.id  # != semester code
    semester_code = None
    # get semester code from semester_json and semester_id
    for semester in semester_json:
        if semester["id"] == semester_id:
            print(
                "Found semester: %s (from %s to %s)"
                % (semester["nameZh"], semester["start"], semester["end"])
            )
            _ = input("Is it correct? [y/N] ")
            if _ == "y":
                semester_code = semester["code"]
                break
    if semester_code is None:
        print("Cannot find semester with id %s" % semester_id)
        exit(-1)
    print("Data loaded with %d courses" % len(lesson_json))
    for c in lesson_json:
        if (
            c["dateTimePlaceText"] is not None
            and "停开" in c["dateTimePlaceText"]
            and not args.import_stopped_course
        ):
            continue

        course = c["course"]
        code = course["code"]
        term = semester_code
        course_kcbh[code] = dict(
            kcid=int(course["id"]),
            kcbh=course["code"],
            name=course["cn"],
            name_eng=course["en"],
            credit=c["credits"],
            course_type=c["courseCategory"]["cn"],
            course_level=c["courseGradation"]["cn"] if c["courseGradation"] else None,
            join_type=c["classType"]["cn"] if c["classType"] else None,
            teaching_type=c["courseType"]["cn"] if c["courseType"] else None,
        )

        if "period" in c and "periodsPerWeek" in c:
            course_kcbh[code]["hours"] = c["period"]
            course_kcbh[code]["hours_per_week"] = c["periodsPerWeek"]

        teacher_names = []
        teachers = c["teacherAssignmentList"]
        for _t in teachers:
            teacher = _t
            teacher_name = teacher["cn"]
            teacher_names.append(teacher_name)
            if teacher_name in teachers_map:
                t = teachers_map[teacher_name]
            else:
                t = Teacher()
            t.name = teacher_name
            try:
                # it seems that catalog data does not have gender
                if teacher["person"]["gender"]["en"] == "Male":
                    t.gender = "male"
                elif teacher["person"]["gender"]["en"] == "Female":
                    t.gender = "female"
                else:
                    t.gender = "unknown"
            except:
                t.gender = "unknown"

            try:
                DWDM = teacher["departmentCode"]
                if DWDM in depts_code_map:
                    t._dept = depts_code_map[DWDM]
                else:
                    print("Teacher department not found " + DWDM + ": " + str(teacher))
            except:
                pass

            if not t.name in teachers_map:
                db.session.add(t)
                teachers_map[t.name] = t
                new_teacher_count += 1
        # sanity check: teachers_map should not have duplication
        # example: a course has several "特邀教师", which breaks following assumption
        if len(teacher_names) != len(set(teacher_names)):
            print("Duplicated teacher names: %s" % teacher_names)
            _ = input("Do you wanna deduplicate teacher names list? [y/N] ")
            if _ == "y":
                teacher_names = list(set(teacher_names))
                print("Deduplicated teachers: %s" % teacher_names)
            else:
                print("Abort.")
                exit(-1)

        course_key = course["cn"] + "(" + ",".join(sorted(teacher_names)) + ")"
        if course_key in courses_map:
            course = courses_map[course_key]
            print("Existing course " + course_key)
        else:
            course_name = course["cn"]
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
            print("New course " + course_key)
            new_course_count += 1

        # update course info
        if c["openDepartment"]["code"] in depts_code_map:
            course.dept_id = depts_code_map[c["openDepartment"]["code"]].id
        else:
            print(
                "Department code "
                + c["openDepartment"]["code"]
                + " not found in "
                + str(c)
            )

        # course term
        term_key = course_key + "@" + str(term)
        if term_key in course_terms_map:
            course_term = course_terms_map[term_key]
            print("Existing course term " + term_key)
        else:
            course_term = CourseTerm()
            db.session.add(course_term)
            course_terms_map[term_key] = course_term
            print("New course term " + term_key)
            new_term_count += 1

        # update course term info
        course_term.course = course
        course_term.term = term
        # change 123456.01 format to the original 12345601 format
        class_code = c["code"].replace(".", "").upper()
        course_term.courseries = class_code
        course_term.class_numbers = class_code

        for key in course_kcbh[code]:
            setattr(course_term, key, course_kcbh[code][key])

        # course class
        unique_key = class_code + "@" + str(term)
        if unique_key in course_classes_map:
            course_class = course_classes_map[unique_key]
            course_class.course = course  # update course mapping
            print("Existing course class " + unique_key)
        else:
            course_class = CourseClass()
            db.session.add(course_class)
            course_classes_map[unique_key] = course_class
            print("New course class " + unique_key)
            new_class_count += 1

        # update course class info
        course_class.course = course
        course_class.term = term
        course_class.cno = class_code

    print("load complete, committing changes to database")
    db.session.commit()
    print("%d new teachers loaded" % new_teacher_count)
    print("%d new courses loaded" % new_course_count)
    print("%d new terms loaded" % new_term_count)
    print("%d new classes loaded" % new_class_count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import courses from public catalog")
    parser.add_argument("--id", type=int, help="semester id")
    parser.add_argument("--semester", type=Path, help="semester json file")
    parser.add_argument("--lesson", type=Path, help="lesson json file")
    parser.add_argument(
        "--import-stopped-course",
        action="store_true",
        help="import stopped (停开) courses",
    )

    args = parser.parse_args()
    # we have merge now, do not drop existing data
    with app.app_context():
        db.create_all()
        load_courses(args)
