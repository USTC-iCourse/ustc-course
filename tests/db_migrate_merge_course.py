#!/usr/bin/env python3
# init_db.py must be executed before running this migration script!

import datetime
import mysql.connector
import sys
import re

sys.path.append('../config')
from default import SQLALCHEMY_DATABASE_URI

m = re.search('://([^:]+):([^@]+)@(\w+)/(\w+)', SQLALCHEMY_DATABASE_URI)
if not m:
    print("Invalid " + SQLALCHEMY_DATABASE_URI)
    sys.exit(1)
conn = mysql.connector.connect(user=m.group(1), password=m.group(2), host=m.group(3), database=m.group(4))
cursor = conn.cursor()

cursor.execute("SET foreign_key_checks = 0")

# course
print("migrating courses...")
cursor.execute("DROP TABLE IF EXISTS old_courses")
cursor.execute("CREATE TABLE old_courses LIKE courses")
cursor.execute("ALTER TABLE old_courses ADD COLUMN teacher_list VARCHAR(200)")
cursor.execute("INSERT INTO old_courses SELECT courses.*, GROUP_CONCAT(DISTINCT teacher_id ORDER BY teacher_id SEPARATOR ' ') AS teacher_list FROM courses LEFT JOIN course_teachers ON courses.id=course_teachers.course_id GROUP BY courses.id")
# NULL does not compare equal to NULL, so replace it with empty string
cursor.execute("UPDATE old_courses SET teacher_list='' WHERE teacher_list IS NULL")

cursor.execute("DROP TABLE IF EXISTS new_courses")
cursor.execute('''CREATE TABLE new_courses (
        id INT(10) PRIMARY KEY AUTO_INCREMENT,
        name VARCHAR(80),
        teacher_list VARCHAR(200),
        dept_id INT(10),
        _image VARCHAR(100),
        INDEX key_name (name),
        FOREIGN KEY (dept_id) REFERENCES depts (id)
)''')
cursor.execute("INSERT INTO new_courses (name, teacher_list, dept_id, _image) SELECT name, teacher_list, dept_id, _image FROM old_courses GROUP BY name, teacher_list")

# course_teachers
print("migrating course_teachers...")
cursor.execute("DROP TABLE IF EXISTS new_course_teachers")
cursor.execute("CREATE TABLE new_course_teachers LIKE course_teachers")
cursor.execute("INSERT INTO new_course_teachers SELECT DISTINCT new_courses.id AS course_id, course_teachers.teacher_id FROM new_courses JOIN old_courses ON new_courses.teacher_list=old_courses.teacher_list AND new_courses.name=old_courses.name JOIN course_teachers ON old_courses.id=course_teachers.course_id")

# course_rates
print("migrating course_rates...")
cursor.execute("DROP TABLE IF EXISTS new_course_rates")
cursor.execute("CREATE TABLE new_course_rates LIKE course_rates")
_rate_properties = [ '_difficulty_total', '_homework_total', '_grading_total', '_gain_total',
        '_rate_total', 'review_count', 'upvote_count', 'downvote_count',
        'follow_count', 'join_count' ]
_rate_key = ', '.join(_rate_properties)
_rate_value = ', '.join([ 'SUM(' + p + ') AS ' + p for p in _rate_properties ])
cursor.execute("INSERT INTO new_course_rates (id, %s) SELECT new_courses.id, %s FROM course_rates JOIN old_courses ON course_rates.id=old_courses.id JOIN new_courses ON old_courses.name=new_courses.name AND old_courses.teacher_list=new_courses.teacher_list GROUP BY old_courses.name, old_courses.teacher_list" %
        (_rate_key, _rate_value))

# course_terms
print("migrating course_terms...")
_term_properties = [ 'term', 'courseries', 'kcid',
    'course_major', 'course_type', 'course_level', 'grading_type',
    'teaching_material', 'reference_material', 'student_requirements',
    'description', 'description_eng', 'introduction', 'homepage',
    'credit', 'hours', 'hours_per_week', 'class_numbers', 'campus',
    'start_week', 'end_week' ]

cursor.execute("DELETE FROM course_terms")
cursor.execute("INSERT INTO course_terms (id, course_id, %s) SELECT old_courses.id, new_courses.id AS course_id, %s FROM old_courses JOIN new_courses ON old_courses.name=new_courses.name AND old_courses.teacher_list=new_courses.teacher_list GROUP BY old_courses.name, old_courses.teacher_list, old_courses.term" %
        (','.join(_term_properties), ','.join(_term_properties)))

# course_classes
print("migrating course_classes...")
# course_classes.id <= courses.id
# course_classes.course_id <= new_courses.id
cursor.execute("DELETE FROM course_classes")
cursor.execute("INSERT INTO course_classes (id, course_id, term, cno) SELECT old_courses.id, new_courses.id AS course_id, term, cno FROM old_courses LEFT JOIN new_courses ON old_courses.name=new_courses.name AND old_courses.teacher_list=new_courses.teacher_list")

# course_time_locations
print("migrating course_time_locations...")
cursor.execute("DROP TABLE IF EXISTS new_course_time_locations")
cursor.execute('''CREATE TABLE new_course_time_locations (
    id INT(10) PRIMARY KEY AUTO_INCREMENT,
    course_id INT(10),
    class_id INT(10),
    term VARCHAR(10),
    weekday INT(10),
    begin_hour INT(10),
    num_hours INT(10),
    location VARCHAR(80),
    note VARCHAR(200),
    FOREIGN KEY (course_id) REFERENCES courses (id),
    FOREIGN KEY (class_id) REFERENCES course_classes (id)
)''')
cursor.execute("INSERT INTO new_course_time_locations (course_id, class_id, term, weekday, begin_hour, num_hours, location, note) SELECT course_classes.course_id, course_classes.id, course_classes.term, weekday, begin_hour, num_hours, location, note FROM course_time_locations JOIN course_classes ON course_time_locations.course_id=course_classes.id")

# follow_course
print("migrating follow_course...")
cursor.execute("DROP TABLE IF EXISTS new_follow_course")
cursor.execute("CREATE TABLE new_follow_course LIKE follow_course")
cursor.execute("INSERT INTO new_follow_course (course_id, user_id) SELECT DISTINCT course_classes.course_id, user_id FROM follow_course JOIN course_classes ON follow_course.course_id=course_classes.id")

# join_course
print("migrating join_course...")
cursor.execute("DROP TABLE IF EXISTS new_join_course")
cursor.execute('''CREATE TABLE new_join_course (
    class_id INT(10),
    student_id VARCHAR(20),
    FOREIGN KEY (class_id) REFERENCES course_classes(id),
    FOREIGN KEY (student_id) REFERENCES students(sno),
    UNIQUE (class_id, student_id)
)''')
cursor.execute("INSERT INTO new_join_course (class_id, student_id) SELECT course_classes.id AS class_id, student_id FROM join_course JOIN course_classes ON join_course.course_id=course_classes.id")

# upvote_course
print("migrating upvote_course...")
cursor.execute("DROP TABLE IF EXISTS new_upvote_course")
cursor.execute("CREATE TABLE new_upvote_course LIKE upvote_course")
cursor.execute("INSERT INTO new_upvote_course (course_id, user_id) SELECT DISTINCT course_classes.course_id, user_id FROM upvote_course JOIN course_classes ON upvote_course.course_id=course_classes.id")

# downvote_course
print("migrating downvote_course...")
cursor.execute("DROP TABLE IF EXISTS new_downvote_course")
cursor.execute("CREATE TABLE new_downvote_course LIKE downvote_course")
cursor.execute("INSERT INTO new_downvote_course (course_id, user_id) SELECT DISTINCT course_classes.course_id, user_id FROM downvote_course JOIN course_classes ON downvote_course.course_id=course_classes.id")

# review_course
print("migrating review_course...")
cursor.execute("DROP TABLE IF EXISTS new_review_course")
cursor.execute("CREATE TABLE new_review_course LIKE review_course")
cursor.execute("INSERT INTO new_review_course (course_id, user_id) SELECT DISTINCT course_classes.course_id, user_id FROM review_course JOIN course_classes ON review_course.course_id=course_classes.id")

# review
print("migrating reviews...")
# we can only save one review for each (course, term, author) tuple
cursor.execute("DROP TABLE IF EXISTS new_reviews")
cursor.execute("CREATE TABLE new_reviews LIKE reviews")
cursor.execute("ALTER TABLE new_reviews ADD COLUMN term VARCHAR(10)")
cursor.execute("ALTER TABLE new_reviews ADD INDEX key_term (term)")
_review_props = ['author_id', 'difficulty', 'homework', 'grading', 'gain', 'rate', 'content', 'publish_time', 'update_time', 'upvote_count', 'comment_count']
cursor.execute("INSERT INTO new_reviews (course_id, term, id, %s) SELECT course_classes.course_id, term, reviews.id, %s FROM reviews JOIN course_classes ON reviews.course_id=course_classes.id GROUP BY course_classes.course_id, author_id, term" %
        (','.join(_review_props), ','.join(_review_props)))

# note
print("migrating notes...")
cursor.execute("DROP TABLE IF EXISTS new_notes")
cursor.execute("CREATE TABLE new_notes LIKE notes")
cursor.execute("ALTER TABLE new_notes ADD COLUMN term VARCHAR(10)")
cursor.execute("ALTER TABLE new_notes ADD INDEX key_term (term)")
cursor.execute("INSERT INTO new_notes (course_id, term, id, author_id, title, content, publish_time, update_time, upvote_count, comment_count) SELECT course_classes.course_id, term, notes.id, author_id, title, content, publish_time, update_time, upvote_count, comment_count FROM notes JOIN course_classes ON notes.course_id=course_classes.id")

# rename all new tables
print("renaming new tables...")

tables = ['courses', 'course_teachers', 'course_rates', 'course_time_locations', 'follow_course', 'join_course', 'upvote_course', 'downvote_course', 'review_course', 'reviews', 'notes']
for table in tables:
    cursor.execute("DROP TABLE IF EXISTS backup_%s" % (table, ))
    cursor.execute("RENAME TABLE %s TO backup_%s, new_%s TO %s" % (table, table, table, table))

cursor.execute("DROP TABLE old_courses")

cursor.execute("SET foreign_key_checks = 1")
# end
