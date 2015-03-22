#!/usr/bin/env python3
from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKeyConstraint
from datetime import datetime
from app import db
#from flask.ext.security import Security, SQLAlchemyUserDatastore, UserMixin, RoleMixin

Roles = ['Admin',
        'User']

folowcourse = db.Table('followcourse',db.metadata,
    db.Column('user_id',db.String(20), db.ForeignKey('users.id')),
    db.Column('course_id',db.String(80), db.ForeignKey('courses.id'))
    )


joincourse= db.Table('joinclass', db.metadata,
    db.Column('student_id', db.String(20), db.ForeignKey('students.sno')),
    db.Column('course_id', db.Integer, db.ForeignKey('courses.id')),
)

roles_users = db.Table('roles_users',
        db.Column('user_id',db.Integer(), db.ForeignKey('users.id')),
        db.Column('role_id', db.Integer(), db.ForeignKey('roles.id')))

#class Role(db.Model, RoleMixin):
#not used for now
class Role(db.Model):
    __tablename__ = 'roles'

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))

#class User(db.Model, UserMixin):
class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer,primary_key=True)
    email = db.Column(db.String(255), unique=True)
    _password = db.Column(db.String(255),nullable=False)
    active = db.Column(db.Boolean())
    #roles = db.relationship('Role',secondary=roles_users, backref=db.backref('users',lazy='dynamic'))
    role = db.Column(db.String(20),default='User')
    register_time = db.Column(db.DateTime(), default=datetime.utcnow)
    confirmed_at = db.Column(db.DateTime())
    last_login_time = db.Column(db.DateTime())
    # We need "use_alter" to avoid circular dependency in FOREIGN KEYs between Student and ImageStore
    avatar = db.Column(db.Integer, db.ForeignKey('image_store.id', name='avatar_storage', use_alter=True))

    courses_following = db.relationship('Course',secondary=folowcourse, backref = 'folowers')
    #needn't anymore
    #reviews = db.relationship('CourseReview',backref='author')
    '''
    notes = db.relationship('CourseNote')
    discussions = db.relationship('CourseForumThread')
    shares = db.relationship('CourseShare')
    '''


    def __repr__(self):
        return '<User {} ({})>'.format(self.email, self.password)




# Students could login
class Student(db.Model):
    __tablename__ = 'students'

    sno = db.Column(db.String(20), unique=True, primary_key=True)
    name = db.Column(db.String(80))
    dept = db.Column(db.String(80))

    description = db.Column(db.Text())

    courses_joined = db.relationship('Course', secondary=joincourse, backref='students')

    def __repr__(self):
        return '<Student {} ({})>'.format(self.name, self.sno)

    @classmethod
    def create(cls, sno, name, dept=None, description=None):
        '''
        creat a Student object and add it to database
        if the student object already exists in the db, it will
            return None.
        :param sno: the student id number
        :param name: the student's name
        :param dept: the department the sutdent belongs to
        :param description:
        '''
        if cls.query.get(sno):
            return None
        else:
            student = cls(sno=sno, name=name, dept=dept, description=description)
            db.session.add(student)
            db.session.commit()
            return student


    # course_type: 计划必修，自由选修……
    def join_course(self, course):
        if not course:
            return None
        self.courses_joined.append(course)
        db.session.add(self)
        db.session.commit()
        return self

    #deprecated
    def follow_course(self, course):
        if not course:
            return None
        self.courses_following.append(course)
        db.session.add(self)
        db.session.commit()
        return self

class Teacher(db.Model):
    __tablename__ = 'teachers'

    tno = db.Column(db.String(20), unique=True, primary_key=True)
    name = db.Column(db.String(80))
    dept = db.Column(db.String(80))

    email = db.Column(db.String(80))
    description = db.Column(db.Text())

    courses = db.relationship('Course',backref='teacher')


    def __repr__(self):
        return '<Teacher {} ({})'.format(self.name, self.tno)

    @classmethod
    def create(cls, tno, name, dept=None,email=None,description=None):
        if cls.query.get(tno):
            return None
        else:
            teacher=cls(tno=tno, name=name, dept=dept, email=email, description=description)
            db.session.add(teacher)
            db.session.commit()
            return teacher



