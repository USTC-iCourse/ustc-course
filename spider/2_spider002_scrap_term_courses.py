"""
脚本运行顺序：2
这个脚本操作对象是：打包成pickle的课程字典文件
所做的操作是：根据课程字典的key，生成url，从教务系统里抓取所有课程页面的html，需要登录。
课程字典的格式是：key=课堂号，value=课程信息列表，列表格式是[kcid（课程id）,课程名称,学分,周学时,教师,上课班级,地点:时间,起止周]
"""

import requests
import pickle
import os

# You should change cookies["JESSIONID"] everytime you signed in
my_cookies = {"JSESSIONID": "4189FC3E84FE5C0D5816CB33E4DF2F34"}
term = input('2014秋季学期: 20141\n2015春季学期: 20142\n2015夏季学期: 20143\n请输入开课学期: ')

try:
    with open('../data/'+term+'_course_dict.pickle', 'rb') as myrestoredata:
        course_dict = pickle.load(myrestoredata)

    for key in course_dict:
        #URL 的生成与数据的具体格式有关,
        #value [kcid（课程id）,课程名称,学分,周学时,教师,上课班级,地点:时间,起止周]
        url = "http://mis.teach.ustc.edu.cn/querystubykcbjh.do?tag=gc&xnxq=" + term + "&kcbjh=" + key + "&kczw=" + course_dict[key][1]

        page = requests.get(url, cookies=my_cookies)
        if not '学号' in page.text:
            raise IOError('请登录综合教务系统，获取 cookie 填入代码中的 JSESSIONID 一栏')

        os.makedirs('../data/' + term, 0o755, exist_ok=True)
        with open("../data/"+term+"/"+ key +".html", "w") as newfile:
            print(page.text, file = newfile)

except IOError as err:
    print('File error: ' + str(err))

except pickle.PickleError as perr:
    print('Pickling error: ' + str(perr))

except ValueError as verr:
    print('Value error: ' + str(verr))
