import re

data=['cg888@mail.ustc.edu.cn',
        'kee@ustc.edu.cn',
        '*li@ustc.edu.cn',
        'ee@ustc.edu.cn@163.com',
        'iii8_ee@ustc.edu.cn'
        ]

regex = re.compile('[a-zA-Z0-9_]+@(mail\.)?ustc\.edu\.cn')

for item in data:
    if regex.fullmatch(item):
        print(item,':',True)
    else:
        print(item,':',False)
