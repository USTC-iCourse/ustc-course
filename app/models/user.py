#!/usr/bin/env python3
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKeyConstraint
from datetime import datetime
from app import db

folowcourse = db.Table('followcourse',db.metadata,
    db.Column('student_id',db.String(20), db.ForeignKey('students.sno')),
    db.Column('course_id',db.String(80), db.ForeignKey('courses.cno'))
    )


joinclass = db.Table('joinclass', db.metadata,
    db.Column('sutdent_id', db.String(20), db.ForeignKey('students.sno')),
    db.Column('class_id', db.Integer, db.ForeignKey('classes.id')),
    #db.Column('term',db.String(10) ,db.ForeignKey('classes.term'))
    #course_type = db.Column(db.String(80), primary_key=True)
    #__table_args__ = (ForeignKeyConstraint([cno, term], [Class.cno, Class.term]), {})

    #course = db.relationship('Course')
    #classes = db.relationship('Class')
    )


# Students could login
class Student(db.Model):
    __tablename__ = 'students'

    sno = db.Column(db.String(20), unique=True, primary_key=True)
    name = db.Column(db.String(80))
    dept = db.Column(db.String(80))

    email = db.Column(db.String(80))
    password = db.Column(db.String(80))
    is_admin = db.Column(db.Boolean(), default=False)

    description = db.Column(db.Text())
    register_time = db.Column(db.DateTime(), default=datetime.utcnow)
    last_login_time = db.Column(db.DateTime())
    # We need "use_alter" to avoid circular dependency in FOREIGN KEYs between Student and ImageStore

    avatar = db.Column(db.Integer, db.ForeignKey('image_store.id', name='avatar_storage', use_alter=True))

    classes = db.relationship('Class', secondary=joinclass, backref='students')
    courses = db.relationship('Course',secondary=folowcourse, backref = 'folowers')
    #courses_following = db.relationship('FollowCourse', backref='student')

    '''
    reviews = db.relationship('CourseReview')
    notes = db.relationship('CourseNote')
    discussions = db.relationship('CourseForumThread')
    shares = db.relationship('CourseShare')
    '''

    def __init__(self, sno, name, dept):
        self.sno = sno
        self.name = name
        self.dept = dept

    def __repr__(self):
        return '<Student {} ({})>'.format(self.name, self.sno)

    # course_type: 计划必修，自由选修……
    def joinClass(self, _class):
        self.classes.append(_class)
        db.session.add(self)
        db.session.commit()

    def followCourse(self, course):
        self.courses.append(course)
        db.session.add(self)
        db.session.commit()

class Teacher(db.Model):
    __tablename__ = 'teachers'

    tno = db.Column(db.String(20), unique=True, primary_key=True)
    name = db.Column(db.String(80))
    dept = db.Column(db.String(80))

    email = db.Column(db.String(80))
    description = db.Column(db.Text())

    classes = db.relationship('Class',backref='teacher')

    def __init__(self, tno, name, dept):
        self.tno = tno
        self.name = name
        self.dept = dept

    def __repr__(self):
        return '<Teacher {} ({})'.format(self.name, self.tno)


