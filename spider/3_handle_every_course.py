"""
脚本运行顺序：3
这个脚本操作的对象是：每个抓取下来的课程信息html文件（包含选课学生）
所做的操作是：做成一个课程学生大字典，每门课是一个元素，课程是key，value是学生和学生信息列表。
输出：一学期所有课程的大字典pickle文件。
"""

import pickle

term = input('2014秋季学期: 20141\n2015春季学期: 20142\n2015夏季学期: 20143\n请输入开课学期: ')

try:
    with open('../data/'+term+'_course_dict.pickle', 'rb') as myrestoredata:
       course_dict = pickle.load(myrestoredata)

    course_student_dict = {}   #课程学生大字典，课程是key，学生名单是value



#######################
# 开始读取文件，处理信息
######################
    for key in course_dict:
        data = open('../data/'+term+'/'+key+'.html')
        student_list = []  #这是每门课的学生名单列表
        new_student = []  #每个学生的信息是一个列表

        for i in range(65):
            data.readline()

        while data.readline().find('align="center" width="10%">') != -1:
            for j in range(4):
                new_student.append(data.readline().split(">")[1].split("<")[0])
            for j in range(5):
                data.readline()

            student_list.append(new_student)
            new_student = []

        data.close()
        course_student_dict[key] = student_list



######################
#处理完毕，写入pickle
######################
    with open('../data/'+term+'_course_student_dict.pickle', 'wb') as course_student_file:
        pickle.dump(course_student_dict, course_student_file)



#############
# Debug info
#############
    print("详细信息： ")
    print("学期：", term)
    print("课程总数：", str(len(course_student_dict)))
    for key in course_student_dict:
        print('课程号：', key)
        print('学生人数：', len(course_student_dict[key]))
        if 0 in course_student_dict[key]:
            print('第一个学生：', course_student_dict[key][0])
        break



###########
# 错误处理
###########
except IOError as err:
    print('File error: ' + str(err))

except pickle.PickleError as perr:
    print('Pickling error: ' + str(perr))

except ValueError as verr:
    print('Value error: ' + str(verr))
