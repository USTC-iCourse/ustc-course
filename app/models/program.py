#!/usr/bin/env python3
from datetime import datetime
from app import db

class Program(db.Model):
    __tablename__ = 'programs'

    id = db.Column(db.Integer, primary_key=True)
    dept_id = db.Column(db.Integer, db.ForeignKey('depts.id'))
    major_id = db.Column(db.Integer, db.ForeignKey('majors.id'))
    name = db.Column(db.String(255))
    name_en = db.Column(db.String(255))
    train_type = db.Column(db.String(50))
    grade = db.Column(db.String(50))

    dept = db.relationship('Dept')
    major = db.relationship('Major')


# CourseGroup is identified by the short course code (e.g. CS1001A)
class CourseGroup(db.Model):
    __tablename__ = 'course_groups'

    code = db.Column(db.String(50), primary_key=True)
    course_gradation = db.Column(db.String(50))
    credits = db.Column(db.Integer)
    introduction = db.Column(db.Text)
    name = db.Column(db.String(255))
    name_en = db.Column(db.String(255))
    seasons = db.Column(db.String(50))
    total_periods = db.Column(db.Integer)


class ProgramCourse(db.Model):
    __tablename__ = 'program_courses'

    id = db.Column(db.Integer, primary_key=True)
    course_group_id = db.Column(db.String(50), db.ForeignKey('course_groups.code'))
    program_id = db.Column(db.Integer, db.ForeignKey('programs.id'))
    dept_id = db.Column(db.Integer, db.ForeignKey('depts.id'))
    compulsory = db.Column(db.Boolean)
    exam_mode = db.Column(db.String(50))
    total_periods = db.Column(db.Integer)
    weeks = db.Column(db.Integer)
    type = db.Column(db.String(50))
    remark = db.Column(db.String(50))
    terms = db.Column(db.String(50))

    course_group = db.relationship('CourseGroup')
    program = db.relationship('Program')
    dept = db.relationship('Dept')


course_group_relation = db.Table('course_group_relations',
    db.Column('code', db.String(50), db.ForeignKey('course_groups.code')),
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id'))
)
