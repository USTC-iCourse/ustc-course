#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import app, db
from app.models import *
import os
from datetime import datetime
import csv
from pypinyin import lazy_pinyin

def dump_teachers():
    f = open('teachers.csv', 'w')
    writer = csv.writer(f)
    header = ['id', 'name', 'name_en', 'email', 'homepage', 'image', 'department']
    writer.writerow(header)

    teachers = Teacher.query.all()
    for t in teachers:
        teacher_depts = dict()
        for course in t.courses:
            if course._dept:
                dept = course._dept.name
                if dept in teacher_depts:
                    teacher_depts[dept] += 1
                else:
                    teacher_depts[dept] = 1
        if len(teacher_depts) > 1:
            print(t.id, t.name, teacher_depts)
        if len(teacher_depts) > 0:
            most_popular_dept = max(teacher_depts, key = teacher_depts.get)
        else:
            most_popular_dept = None

        name_list = lazy_pinyin(t.name)
        xing = name_list[0].capitalize()
        ming = ""
        for m in name_list[1:]:
            ming += m
        if ming == "":
            name_en = xing
        else:
            name_en = xing + " " + ming.capitalize()

        row = [t.id, t.name, name_en, t.email, t.homepage, t.image, most_popular_dept]
        writer.writerow(row)

    f.close()


dump_teachers()
