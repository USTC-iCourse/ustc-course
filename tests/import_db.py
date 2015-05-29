#!/usr/bin/env python3
import sys
sys.path.append('..')  # fix import directory

from app import app, db
from app.models import *
from datetime import datetime

BASEDIR = '../data/misteach'

def parse_file(filename):
    data = []
    with open(BASEDIR + '/' + filename) as f:
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

depts_map = dict()
depts_code_map = dict()

def load_depts():
    existing_depts = Course.query.all()
    for dept in existing_depts:
        depts_map[dept.id] = dept

    count = 0
    for c in parse_file('JT_DWDM.txt'):
        if int(c['DWDM']) in depts_map:
            dept = depts_map[int(c['DWDM'])]
        else:
            dept = Dept()
            dept.id = int(c['DWDM'])
        dept.name = c['DWMC']
        dept.name_eng = c['YWMC']
        dept.code = c['DWBH']

        if not dept in db.session:
            db.session.add(dept)
        count+=1
        depts_map[dept.id] = dept
        depts_code_map[dept.code] = dept

    db.session.commit()
    print('%d departments loaded' % count)

classes_map = dict()

def load_classes():
    existing_classes = DeptClass.query.all()
    for c in existing_classes:
        classes_map[c.id] = c

    count = 0
    for c in parse_file('JT_XZBJB.txt'):
        if int(c['BJID']) in classes_map:
            dept_class = classes_map[int(c['BJID'])]
        else:
            dept_class = DeptClass()
            dept_class.id = int(c['BJID'])
        dept_class.name = c['XZBJMC']
        if c['SSYX'] and not int(c['SSYX']) in depts_map:
            print('Department ' + c['SSYX'] + ' not found for class ' + str(c))
        else:
            dept_class.dept = int(c['SSYX'])
        
        if not dept_class in db.session:
            db.session.add(dept_class)
        count+=1
        classes_map[dept_class.id] = dept_class.name

    db.session.commit()
    print('%d classes loaded' % count)

majors_map = dict()

def load_majors():
    existing_majors = Major.query.all()
    for major in existing_majors:
        majors_map[major.id] = major

    count = 0
    for c in parse_file('JT_ZYDM.txt'):
        if int(c['ZYDM']) in majors_map:
            major = majors_map[int(c['ZYDM'])]
        else:
            major = Major()
            major.id = int(c['ZYDM'])
        major.name = c['ZYMC']
        major.name_eng = c['YWMC']
        major.code = c['ZYBH']

        if not major in db.session:
            db.session.add(major)
        count+=1
        majors_map[major.id] = major.name

    db.session.commit()
    print('%d majors loaded' % count)

titles_map = dict()

def load_titles():
    count = 0
    for c in parse_file('JT_TITLES.txt'):
        titles_map[c['ZCDM']] = c['ZCMC']
        count+=1

    print('%d titles loaded' % count)

students = dict()
students_map = dict()

def load_students():
    existing_students = Student.query.all()
    for stu in existing_students:
        students_map[stu.sno] = stu

    count = 0
    for c in parse_file('XJ_XSBYMDB.txt'):
        if c['SNO'] in students_map:
            stu = students_map[c['SNO']]
        else:
            stu = Student()
            stu.sno = c['SNO']
        stu.name = c['XM']

        if c['XB'] == '1':
            stu.gender = 'male'
        elif c['XB'] == '2':
            stu.gender = 'female'
        else:
            stu.gender = 'unknown'

        if c['SZYX']:
            if int(c['SZYX']) in depts_map:
                stu._dept = depts_map[int(c['SZYX'])]
            elif int(c['SZYX']) > 0:
                print('Department ' + c['SZYX'] + ' not found for student ' + str(c))

        if c['XZBJ']:
            if int(c['XZBJ']) in classes_map:
                stu.dept_class_id = int(c['XZBJ'])
            elif int(c['XZBJ']) > 0:
                print('Class ' + c['XZBJ'] + ' not found for student ' + str(c))

        if c['SXZY']:
            if int(c['SXZY']) in majors_map:
                stu.major_id = int(c['SXZY'])
            elif int(c['SXZY']) > 0:
                print('Major ' + c['SXZY'] + ' not found for student ' + str(c))

        students[stu.sno] = stu;

    for c in parse_file('XJ_XSXXB.txt'):
        if c['SNO'] in students:
            stu = students[c['SNO']]
            stu.email = c['EMAIL']

            del students[c['SNO']] # remove the student after added to db
        else:
            stu = Student()
            stu.sno = c['SNO']
            stu.name = c['XM']
            stu.email = c['EMAIL']
            if c['XB'] == '1':
                stu.gender = 'male'
            elif c['XB'] == '2':
                stu.gender = 'female'
            else:
                stu.gender = 'unknown'
            if c['LQYX'] and int(c['LQYX']) in depts_map:
                stu._dept = depts_map[int(c['LQYX'])]
            else:
                print('Department ' + c['LQYX'] + ' not found for student ' + str(c))

        if not stu in db.session:
            db.session.add(stu)
        count+=1
        students_map[stu.sno] = stu;

    # students in XJ_XSBYMDB but not in XJ_XSXXB
    for sno in students:
        stu = students[sno]
        if not stu in db.session:
            db.session.add(stu)
        count+=1
        students_map[stu.sno] = stu

    db.session.commit()
    print('%d students loaded' % count)

teachers_map = dict()

def load_teachers():
    existing_teachers = Teacher.query.all()
    for t in existing_teachers:
        teachers_map[t.id] = t

    count = 0
    for c in parse_file('T_YHXXB.txt'):
        if int(c['YHID']) in teachers_map:
            t = teachers_map[int(c['YHID'])]
        else:
            t = Teacher()
            t.id = int(c['YHID'])
        t.name = c['XM']
        if c['XBDM'] == '1':
            t.gender = 'male'
        elif c['XBDM'] == '2':
            t.gender = 'female'
        else:
            t.gender = 'unknown'
        if c['DWDM'] and int(c['DWDM']) in depts_code_map:
            t._dept = depts_code_map[int(c['DWDM'])]
        t.email = c['EMAIL']
        t.title = titles_map[c['TITLEDM']] if c['TITLEDM'] in titles_map else None
        t.office_phone = c['OFFICEPHONE']
        t.description = c['INTRODUCTION']

        if not t in db.session:
            db.session.add(t)
        count+=1
        teachers_map[t.id] = t

    db.session.commit()
    print('%d teachers loaded' % count)

# We should load all existing courses, because SQLAlchemy does not support .merge on non-primary-key,
# and we want to preserve course ID (primary key) for each (cno, term) pair.
courses_map = dict()

def load_courses(insert=True):
    course_major_dict = dict(
        ES   =   '电子科学技术',
        NU   =   '核科学类',
        IS   =   '信息安全',
        PS   =   '政治学',
        FL   =   '外国语言',
        CO   =   '传播学',
        SH   =   '科学技术史',
        HS   =   '人文社科类',
        SW   =   '软件工程',
        PE   =   '体育',
        LW   =   '法学类',
        AY   =   '天文学',
        MA   =   '数学',
        PH   =   '物理学',
        EM   =   '经济管理',
        CH   =   '化学',
        MS   =   '材料科学',
        GP   =   '地球物理',
        AE   =   '大气科学',
        GE   =   '地球化学',
        EN   =   '环境科学',
        BI   =   '生物学',
        ME   =   '力学',
        PI   =   '仪器与机械类',
        TS   =   '动力工程',
        SE   =   '安全工程',
        IN   =   '信息类',
        CN   =   '控制科学',
        CS   =   '计算机科学技术',
    )

    course_type_dict = dict()
    course_type_dict['1'] = '本科计划内课程'
    course_type_dict['2'] = '入学考试'
    course_type_dict['4'] = '全校公修'
    course_type_dict['5'] = '研究生课'
    course_type_dict['7'] = '外校交流课程'
    course_type_dict['8'] = '双学位'
    course_type_dict['15'] = '体育选项'
    course_type_dict['16'] = '英语拓展'
    course_type_dict['99'] = '本科计划内/全校公修'

    course_level_dict = [
        None,
        '全校通修',
        '学科群基础课',
        '专业核心课',
        '专业硕士课',
        '专业方向课',
        '本研衔接',
        '硕士层次',
        '博士层次',
    ]

    grading_type_dict = [
        None,
        '百分制',
        '二分制',
        '五分制',
    ]
    
    existing_courses = Course.query.all()
    for c in existing_courses:
        unique_key = c.cno + '|' + c.term
        courses_map[unique_key] = c

    int_allow_empty = lambda string: int(string) if string.strip() else 0
    course_kcbh = {}
    for c in parse_file('JH_KC_ZK.txt'):
        course_kcbh[c['KCBH']] = dict(
            kcid = int(c['KCID']),
            kcbh = c['KCBH'],
            name = c['KCZW'],
            name_eng = c['KCYW'],
            credit = c['XF'],
            hours = c['XS'],
            hours_per_week = c['ZXS'],
            teaching_material = c['JC'],
            reference_material = c['CKS'],
            student_requirements = c['XSYQ'],
            description = c['KCJJ'],
            description_eng = c['YWJJ'],
            course_major = course_major_dict[c['XKLB']] if c['XKLB'] in course_major_dict else None,
            course_type = course_type_dict[c['KCFC']] if c['KCFC'] in course_type_dict else None,
            grading_type = grading_type_dict[int_allow_empty(c['PFZ'])],
        )

    count = 0
    for c in parse_file('MV_PK_PKJGXS.txt'):
        if not c['KCBH'] in course_kcbh:
            print('Course ' + c['KCBH'] + ' exists in MV_PK_PKJGXS but not in JH_KC_ZK: ' + str(c))
            continue

        unique_key = c['KCBJH'].upper() + '|' + c['XQ']
        if unique_key in courses_map:
            course = courses_map[unique_key]
        else:
            course = Course()
            course.term = c['XQ']
            course.cno = c['KCBJH'].upper()
            db.session.add(course)

            course_rate = CourseRate()
            course_rate.course = course
            db.session.add(course_rate)

        course.courseries = c['KCBH']
        if c['DWBH'] in depts_code_map:
            course.dept_id = depts_code_map[c['DWBH']].id
        else:
            print('Department code ' + c['DWBH'] + ' not found in ' + str(c))
        course.class_numbers = c['SKBJH']
        course.start_week = c['QSZ']
        course.end_week = c['JZZ']
        course.course_level = course_level_dict[int_allow_empty(c['KCCCDM'])]

        for key in course_kcbh[c['KCBH']]:
            setattr(course, key, course_kcbh[c['KCBH']][key])

        teacher_ids = [ int(tid) for tid in c['JS'].split(',') ] if c['JS'] else []
        for teacher_id in teacher_ids:
            if not teacher_id in teachers_map:
                print('Teacher ID ' + str(teacher_id) + ' not found for course ' + str(c))
                continue
            course.teachers.append(teachers_map[teacher_id])

        courses_map[unique_key] = course
        count+=1

    db.session.commit()
    print('%d courses loaded' % count)

course_locations_map = dict()

def load_course_locations():
    int_allow_empty = lambda string: int(string) if string.strip() else None
    def get_begin_hour(code, num_hours):
        if code == '1': # (1,2)
            return 1
        elif code == '2': # (3,4) (3,4,5)
            return 3
        elif code == '3': # (6,7)
            return 6
        elif code == '4': # (8,9) (8,9,10)
            return 8
        elif code == '5': # 晚上
            return 11
        elif code == 'a': # (7,8) (6,7,8)
            return 7 if num_hours == 2 else 6
        elif code == 'b': # (9,10)
            return 9
        else:
            return None

    count = 0
    for c in parse_file('PK_PKJGB.txt'):
        unique_key = c['KCBJH'].upper() + '|' + c['ND'] + c['XQ']
        if not unique_key in courses_map:
            print('Course not found: ' + str(c))
            continue
        course = courses_map[unique_key]

        loc = CourseTimeLocation()
        loc.course = course
        loc.location = c['JSBH']
        if len(c['SJPDM']) == 2:
            loc.weekday = int_allow_empty(c['SJPDM'][0])
            loc.num_hours = int_allow_empty(c['KS'])
            loc.begin_hour = get_begin_hour(c['SJPDM'][1], c['KS'])
        else:
            loc.note = c['BEIY1']

        db.session.merge(loc)
        count+=1

    db.session.commit()
    print('%d course locations loaded' % count)

def load_join_course():
    courses_id_map = {}

    existing_students = Student.query.all()
    for stu in existing_students:
        students_map[stu.sno] = stu

    existing_courses = Course.query.all()
    for c in existing_courses:
        unique_key = c.cno + '|' + c.term
        courses_map[unique_key] = c
        courses_id_map[str(c.kcid) + '|' + c.term] = c

    count = 0
    for c in parse_file('XK_XKJGB.txt'):
        unique_key = c['KCBJH'].upper() + '|' + c['XNXQ']
        if not unique_key in courses_map:
            print('Course not found:' + str(c))
            continue
        course = courses_map[unique_key]
        if c['XH'] not in students_map:
            print('Student id ' + c['XH'] + ' not found: ' + str(c))
            continue
        student = students_map[c['XH']]
        if not student in course.students:
            course.students.append(student)
            count+=1

    # join course info before 2012 does not exist in XKJGB
    for c in parse_file('CJ_CJXXB.txt'):
        if float(c['CJ']) < 0: # 可能已经退课
            continue
        if float(c['CJ']) > 100: # 二等级或五等级制课程，正常录入
            pass
        cno_key = c['KCBJH'].upper() + '|' + c['XQ']
        id_key = str(c['KCID']) + '|' + c['XQ']
        if cno_key in courses_map:
            course = courses_map[cno_key]
        elif id_key in courses_id_map:
            course = courses_id_map[id_key]
        else:
            print('Course ID key ' + id_key + ' and CNO key ' + cno_key + ' not found:' + str(c))
            continue

        if c['SNO'] not in students_map:
            print('Student id ' + c['SNO'] + ' not found: ' + str(c))
            continue
        student = students_map[c['SNO']]
        if student not in course.students:
            course.students.append(student)
            count+=1

    db.session.commit()
    print('%d xuanke info loaded' % count)

def load_grad_students(insert=True):
    count = 0
    for c in parse_file('V_XSXX_GS.txt'):
        if c['XUEHAO'] in students_map:
            stu = students_map[c['XUEHAO']]
        else:
            stu = Student()
            stu.sno = c['XUEHAO']
        stu.name = c['NAME']
        if c['DEPT_CODE'] and c['DEPT_CODE'] in depts_code_map:
            stu._dept = depts_code_map[c['DEPT_CODE']]

        if c['XINGBIE'] == '1':
            stu.gender = 'male'
        elif c['XINGBIE'] == '2':
            stu.gender = 'female'
        else:
            stu.gender = 'unknown'

        if not stu in db.session:
            db.session.add(stu)
        count+=1
        students_map[stu.sno] = stu

    db.session.commit()
    print('%d grad students loaded' % count)

def load_grad_join_course():
    count = 0
    for c in parse_file('GRAD_XK_GCB.txt'):
        unique_key = c['KCBJH'].upper() + '|' + c['XNXQ']
        if not unique_key in courses_map:
            print('Course not found:' + str(c))
            continue
        course = courses_map[unique_key]
        if c['SNO'] not in students_map:
            print('Student id ' + c['SNO'] + ' not found: ' + str(c))
            continue
        student = students_map[c['SNO']]
        course.students.append(student)
        count+=1

    for c in parse_file('GRAD_XK_JGB.txt'):
        unique_key = c['KCBJH'].upper() + '|' + c['XNXQ']
        if not unique_key in courses_map:
            print('Course not found:' + str(c))
            continue
        course = courses_map[unique_key]
        if c['SNO'] not in students_map:
            print('Student id ' + c['SNO'] + ' not found: ' + str(c))
            continue
        student = students_map[c['SNO']]
        if not student in course.students:
            course.students.append(student)
            count+=1
            print(count)

    db.session.commit()
    print('%d grad xuanke info loaded' % count)


# we have merge now, do not drop existing data
#db.drop_all()
db.create_all()
load_depts()
load_classes()
load_majors()
load_titles()
load_teachers()
load_courses()
load_students()
load_course_locations()
load_join_course()
load_grad_students()
load_grad_join_course()
