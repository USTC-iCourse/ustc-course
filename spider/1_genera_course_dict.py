"""
脚本运行顺序：１（从１开始）
所做的操作是：把课程信息从html中剥离出来，并且打包成课程字典的pickle文件
课程字典的格式是：key=课堂号，value=课程信息列表，列表格式是[kcid（课程id）,课程名称,学分,周学时,教师,上课班级,地点:时间,起止周]
"""


import pickle
import requests
import os

term = input('2014秋季学期: 20141\n2015春季学期: 20142\n2015夏季学期: 20143\n请输入开课学期: ')

#开始处理
############################
try:
    print('Sending request to 综合教务系统')
    r = requests.post("http://mis.teach.ustc.edu.cn/kbcx.do", data={"xq": "20142", "xklb": "all", "cxfs": 0})
    print('Processing Data...')
    omit_lines = 818
    data_iter = iter(r.text.split('\n')[omit_lines: ])

    course_dict = {}  #一学期所有的课程是一个大字典, 每个课程的value是一个列表

    while next(data_iter).find('align="center" width="5%">') != -1:
        course_key = next(data_iter).split(">")[1].split("</td")[0].strip()
        course_dict[course_key] = []  #每个课程的value是一个列表
        #列表格式是[kcid（课程id）,课程名称,学分,周学时,教师,上课班级,地点:时间,起止周]
        newline = next(data_iter)
        #课程链接这一项因为格式不对，需要特殊处理
        course_dict[course_key].append(newline.split('kcid=')[1].split('" target')[0])
        course_dict[course_key].append(newline.split('color="blue">')[1].split('</font>')[0])
        for j in range(6):
            newline = next(data_iter)
            newline = newline.replace('&nbsp;', '')
            newline = newline.replace('<br/>', ';')
            course_dict[course_key].append(newline.split(">")[1].split("</td")[0])
        for j in range(3):
            next(data_iter)

    os.makedirs('../data', 0o755, exist_ok=True)
    with open('../data/'+term+'_course_dict.pickle', 'wb') as course_dict_file:
        pickle.dump(course_dict, course_dict_file)


#debug info
    print(course_dict)
    print("Detail: ")
    print("Term:", term)
    print("len(course_dict):", str(len(course_dict)))
    print("Format:","'课堂号': ['课程id', '课程名称', '学分', '周学时', '教师', '上课班级', '地点：时间', '起止周']")


except IOError as err:
    print('File error: ' + str(err))

except pickle.PickleError as perr:
    print('Pickling error: ' + str(perr))

except ValueError as verr:
    print('Value error: ' + str(verr))
