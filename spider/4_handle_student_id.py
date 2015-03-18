"""
脚本运行顺序：4
这个脚本操作对象：课程学生大字典pickle文件
所做操作：把每个学生从所有课程中剥离出来，获得学生大字典，key是学生学号，value是学生本学期的所有课程
"""

import pickle

term = input('2014秋季学期: 20141\n2015春季学期: 20142\n2015夏季学期: 20143\n请输入开课学期: ')


try:
    # 从每学期“课程学生”文件中导入课程学生数据，是一个大字典
    with open('../data/'+term+'_course_student_dict.pickle', 'rb') as course_student_file:
        course_student_dict = pickle.load(course_student_file)

    # 建立一个学生字典，key是学生学号，value是学生信息（包括姓名，院系，这学期所上的课程）
    all_student_dict = {}

    # 建立一个学生姓名学号对应的列表，格式是['张静宁', 'PB14203209', '苏晓文', 'PB14000537' ]
    # 为了方便以学生姓名搜索
    student_name_id = []




    # 根据课程信息列表，把所有课程学生扫一遍，建立all_student_dict字典
    for key in course_student_dict:
        #key是课堂号

        for each_student in course_student_dict[key]:
            # each_student 是一个带有学生信息的列表
            # 像这样 ['PB14001067', '刘传奇', '数学科学学院', '计划必修']
            # 所以 each_student[0] 才是 学生key
            if each_student[0] not in all_student_dict:
                all_student_dict[each_student[0]] = []
                all_student_dict[each_student[0]].append(each_student[1])      #value[0] 是学生姓名
                all_student_dict[each_student[0]].append(each_student[2])      #value[1] 是学生院系
                all_student_dict[each_student[0]].append([])                   #value[2] 是学生一学期内所有课程信息，是个列表

                # 把这个学生加到姓名学号列表上
                student_name_id.append(each_student[1])
                student_name_id.append(each_student[0])

            # 不管学生在不在字典中，每门课程信息都应该登记一次，登记的格式是 ['多变量微积分', '计划必修']
            all_student_dict[each_student[0]][2].append([key, each_student[3]])




    with open("../data/"+term+"_all_student_dict.pickle", "wb") as all_student_file:
        pickle.dump(all_student_dict, all_student_file)
    with open("../data/"+term+"_student_name_id.pickle", "wb") as student_name_file:
        pickle.dump(student_name_id, student_name_file)




#debug info
    print("详细信息： ")
    print("学期：", term)
    print("学生总数：", str(len(all_student_dict)))
    for key in all_student_dict:
        print('学生学号：', key)
        print('学生信息：', all_student_dict[key])
        print('本学期课程数:', len(all_student_dict[key][2]))
        break




except IOError as err:
    print('File error: ' + str(err))

except pickle.PickleError as perr:
    print('Pickling error: ' + str(perr))

except ValueError as verr:
    print('Value error: ' + str(verr))
