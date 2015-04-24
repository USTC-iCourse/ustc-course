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
    count = 0
    for c in parse_file('JT_DWDM.txt'):
        dept = Dept()
        dept.id = c['DWDM']
        dept.name = c['DWMC']
        dept.name_eng = c['YWMC']
        dept.code = c['DWBH']

        db.session.merge(dept)
        count+=1
        depts_map[dept.id] = dept.name
        depts_code_map[dept.code] = dept.id

    db.session.commit()
    print('%d departments loaded' % count)

classes_map = dict()

def load_classes():
    count = 0
    for c in parse_file('JT_XZBJB.txt'):
        dept_class = DeptClass()
        dept_class.id = c['BJID']
        dept_class.name = c['XZBJMC']
        if c['SSYX'] and not c['SSYX'] in depts_map:
            print('Department ' + c['SZYX'] + ' not found for class ' + str(c))
        else:
            dept_class.dept = c['SSYX']
        
        db.session.merge(dept_class)
        count+=1
        classes_map[dept_class.id] = dept_class.name

    db.session.commit()
    print('%d classes loaded' % count)

majors_map = dict()

def load_majors():
    count = 0
    for c in parse_file('JT_ZYDM.txt'):
        major = Major()
        major.id = c['ZYDM']
        major.name = c['ZYMC']
        major.name_eng = c['YWMC']
        major.code = c['ZYBH']

        db.session.merge(major)
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
    count = 0
    for c in parse_file('XJ_XSBYMDB.txt'):
        stu = Student()
        stu.sno = c['SNO']
        stu.name = c['XM']

        if c['XB'] == 1:
            stu.gender = 'male'
        elif c['XB'] == 2:
            stu.gender = 'female'
        else:
            stu.gender = 'unknown'

        if c['SZYX'] in depts_map:
            stu.dept_id = int(c['SZYX'])
        elif len(c['SZYX']) > 0:
            print('Department ' + c['SZYX'] + ' not found for student ' + str(c))

        if c['XZBJ'] in classes_map:
            stu.dept_class_id = int(c['XZBJ'])
        elif len(c['XZBJ']) > 0:
            print('Class ' + c['XZBJ'] + ' not found for student ' + str(c))

        if c['SXZY'] in majors_map:
            stu.major_id = int(c['SXZY'])
        elif len(c['SXZY']) > 0:
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
            if c['XB'] == 1:
                stu.gender = 'male'
            elif c['XB'] == 2:
                stu.gender = 'female'
            else:
                stu.gender = 'unknown'
            if c['LQYX'] in depts_map:
                stu.dept_id = int(c['LQYX'])
            else:
                print('Department ' + c['LQYX'] + ' not found for student ' + str(c))

        db.session.merge(stu)
        count+=1
        students_map[stu.sno] = stu;

    # students in XJ_XSBYMDB but not in XJ_XSXXB
    for sno in students:
        db.session.merge(students[sno])
        count+=1
        students_map[stu.sno] = stu;

    db.session.commit()
    print('%d students loaded' % count)

teachers_map = dict()

def load_teacher():
    count = 0
    for c in parse_file('T_YHXXB.txt'):
        t = Teacher()
        t.id = c['YHID']
        t.name = c['XM']
        if c['XBDM'] == 1:
            t.gender = 'male'
        elif c['XBDM'] == 2:
            t.gender = 'female'
        else:
            t.gender = 'unknown'
        t.dept_id = int(c['DWDM']) if c['DWDM'] in depts_map else None
        t.email = c['EMAIL']
        t.title = titles_map[c['TITLEDM']] if c['TITLEDM'] in titles_map else None
        t.office_phone = c['OFFICEPHONE']
        t.description = c['INTRODUCTION']

        db.session.merge(t)
        count+=1
        teachers_map[t.id] = t

    db.session.commit()
    print('%d teachers loaded' % count)

# We should load all existing courses, because SQLAlchemy does not support .merge on non-primary-key,
# and we want to preserve course ID (primary key) for each (cno, term) pair.
courses_map = dict()

def load_course(insert=True):
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
            kcid = c['KCID'],
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

        info = course_kcbh[c['KCBH']]
        info['term'] = c['XQ']
        info['cno'] = c['KCBJH'].upper()
        info['courseries'] = c['KCBH']
        info['dept'] = c['DWMC']
        info['class_numbers'] = c['SKBJH']
        info['start_week'] = c['QSZ']
        info['end_week'] = c['JZZ']
        info['course_level'] = course_level_dict[int_allow_empty(c['KCCCDM'])]

        unique_key = c['KCBJH'].upper() + '|' + c['XQ']
        if unique_key in courses_map:
            course = courses_map[unique_key]
        else:
            course = Course()
            db.session.add(course)

            course_rate = CourseRate()
            course_rate.course = course
            db.session.add(course_rate)

        for key in info:
            setattr(course, key, info[key])

        teacher_ids = c['JS'].split(',') if c['JS'] else []
        for teacher_id in teacher_ids:
            if not teacher_id in teachers_map:
                print('Teacher ID %s not found for course %s', teacher_id, str(c))
                continue
            course.teachers.append(teachers_map[teacher_id])

        courses_map[unique_key] = course
        count+=1

    db.session.commit()
    print('%d courses loaded' % count)

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
        course.students.append(student)
        count+=1

    # join course info before 2012 does not exist in XKJGB
    for c in parse_file('CJ_CJXXB.txt'):
        if float(c['CJ']) < 0: # 可能已经退课
            continue
        if float(c['CJ']) > 100: # 二等级或五等级制课程，正常录入
            pass
        unique_key = c['KCBJH'].upper() + '|' + c['XQ']
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

    db.session.commit()
    print('%d xuanke info loaded' % count)

def load_grad_students(insert=True):
    count = 0
    for c in parse_file('V_XSXX_GS.txt'):
        if c['XUEHAO'] in students_map:
            print('Graduate student found in undergradute map: ' + str(c))
            continue

        stu = Student()
        stu.sno = c['XUEHAO']
        stu.name = c['NAME']
        if c['DEPT_CODE'] in depts_code_map:
            stu.dept_id = depts_code_map[c['DEPT_CODE']]

        if c['XINGBIE'] == 1:
            stu.gender = 'male'
        elif c['XINGBIE'] == 2:
            stu.gender = 'female'
        else:
            stu.gender = 'unknown'

        db.session.merge(stu)
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

    db.session.commit()
    print('%d grad xuanke info loaded' % count)


# we have merge now, do not drop existing data
#db.drop_all()
db.create_all()
load_depts()
load_classes()
load_majors()
load_titles()
load_students()
load_teacher()
load_course()
load_course_locations()
load_join_course()
load_grad_students()
load_grad_join_course()
