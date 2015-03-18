"""
脚本运行顺序：2
这个脚本操作对象是：打包成pickle的课程字典文件
所做的操作是：根据课程字典的key，生成url，从教务系统里抓取所有课程页面的html，需要登录。
课程字典的格式是：key=课堂号，value=课程信息列表，列表格式是[kcid（课程id）,课程名称,学分,周学时,教师,上课班级,地点:时间,起止周]
"""

import requests
import pickle

# You should change cookies["JESSIONID"] everytime you signed in
my_cookies = {"pgv_pvi":"7886302208", "__utma": "63887786.357939715.1420618208.1421380394.1422108680.4", " __utmz": "63887786.1425197280.5.2.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=(not%20provided)", "_gscu_1103646635": "20618766mew2xs15", "_ga": "GA1.3.2036932779.1422282491", "JSESSIONID": "9863C5650F4678B3A84DC1E9DEF4B914"}
term = input('2014秋季学期: 20141\n2015春季学期: 20142\n2015夏季学期: 20143\n请输入开课学期: ')

try:
    with open('../data/'+term+'_course_dict.pickle', 'rb') as myrestoredata:
        course_dict = pickle.load(myrestoredata)

    for key in course_dict:
        #URL 的生成与数据的具体格式有关,
        #value [kcid（课程id）,课程名称,学分,周学时,教师,上课班级,地点:时间,起止周]
        url = "http://mis.teach.ustc.edu.cn/querystubykcbjh.do?tag=gc&xnxq=" + term + "&kcbjh=" + key + "&kczw=" + course_dict[key][1]

        page = requests.get(url, cookies=my_cookies)

        with open("../"+term+"/"+ key +".html", "w") as newfile:
            print(page.text, file = newfile)

except IOError as err:
    print('File error: ' + str(err))

except pickle.PickleError as perr:
    print('Pickling error: ' + str(perr))

except ValueError as verr:
    print('Value error: ' + str(verr))
