'''
将数据导入到数据库
如果为课程指定教师，则课程应该在创建教师后再创建。
'''
from app.models import Course, Student, Teacher

def create_course(cno, term ,name, dept=None, description=None, credit=0, hours=0,
        class_numbers=None, time_location=None, teacher=None):
    ''' creat a course in the database,
    :param con: 课程号(必须)
    :param term: 学期号(必须)
    :param name: 课程名(必须)
    :param dept: 学院
    :param description: 课程描述
    :param credit:  学分
    :param hours: 学时
    :param class_numbers: 班级号
    :param time_location: pass
    :param teacher: 教师对象 Teacher.如果存在，则为该课程添加教师。
    '''
    course=Course.create(cno=cno, term=term,name=name, dept=dept,
            description=description, credit=credit, hours=hours,
            class_numbers=class_numbers, time_location=time_location)
    if teacher:
        course.teacher=teacher
        course = course.save()
    return course

def create_student(sno, name, dept=None, description=None):
    ''' create a student in the database
    :param sno: 学号，unique,必需
    :param name: 姓名
    :param dept: 学院
    :param description: 简介
    '''
    student = Student.create(sno,name,dept,description)
    return student

def create_teacher(tno, name, dept=None,email=None,description=None):
    '''create a teacher in the database
    :param tno: 教工号，主键
    :param name: 姓名
    :param dept: 院系
    :param email: 邮箱
    :param description: 介绍
    '''
    teacher = Teacher.create(tno, name, dept, email, description)
    return teacher

def _test():
    cno='xx000000'
    term='20142'
    name='数学'
    dept='11'
    description='it is a test'

    sno='SA14011088'
    s_name = '常振'

    tno='XX1100011'
    t_name='张三'
    email='test@test.com'


    create_course(cno,term,name,dept,description)
    create_student(sno,s_name, dept, description)
    courses = Course.query.filter_by(cno=cno).all()
    students = Student.query.filter_by(sno=sno).all()
    for item in courses:
        print(item.id,item)
    for item in students:
        print(item.sno,item)

    create_teacher(tno, t_name, dept,email,description)
    teachers = Teacher.query.filter_by(tno=tno).all()
    for item in teachers:
        print(item.tno, item)

if __name__ == '__main__':
    _test()
