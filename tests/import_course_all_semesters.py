#!/usr/bin/env python3
import sys
import os
import requests
import lxml.html
import subprocess

os.chdir(os.path.dirname(__file__))
sys.path.append('..')  # fix import directory

if len(sys.argv) != 2:
    print('Usage: ' + sys.argv[0] + ' <cookie for jw.ustc.edu.cn>')
    sys.exit(1)
cookie = sys.argv[1]
if cookie.startswith('cookie: '):
    cookie = cookie[len('cookie:'):].strip()

folder = '../data/courses-jw.ustc'
if not os.path.exists(folder):
    os.makedirs(folder)

headers = {
    'cookie': cookie,
    'accept': 'application/json, text/javascript, */*; q=0.01',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36',
    'x-requested-with': 'XMLHttpRequest',
    'authority': 'jw.ustc.edu.cn',
    'referer': 'https://jw.ustc.edu.cn/for-std/lesson-search/index/4367'
}

index_url = 'https://jw.ustc.edu.cn/for-std/lesson-search/index/4367'
r = requests.get(index_url, headers=headers)
doc = lxml.html.fromstring(r.text)
options = doc.xpath('//select[@id="semester"]/option')
if len(options) == 0:
    print('Semesters not found, please check whether cookie is valid')
    sys.exit(1)

print('Found ' + str(len(options)) + ' semesters')
for option in options:
    semester_id = option.attrib['value']
    semester_name = option.text
    echo_text = 'semester ' + semester_name + ' (ID=' + semester_id + ')'

    print('Downloading ' + echo_text)
    lesson_url = 'https://jw.ustc.edu.cn/for-std/lesson-search/semester/' + semester_id + '/search/4367?courseCodeLike=&codeLike=&educationAssoc=&courseNameZhLike=&teacherNameLike=&schedulePlace=&classCodeLike=&courseTypeAssoc=&classTypeAssoc=&campusAssoc=&teachLangAssoc=&roomTypeAssoc=&examModeAssoc=&requiredPeriodInfo.totalGte=&requiredPeriodInfo.totalLte=&requiredPeriodInfo.weeksGte=&requiredPeriodInfo.weeksLte=&requiredPeriodInfo.periodsPerWeekGte=&requiredPeriodInfo.periodsPerWeekLte=&limitCountGte=&limitCountLte=&majorAssoc=&majorDirectionAssoc=&queryPage__=1%2C100000&_=1656750360507'
    r = requests.get(lesson_url, headers=headers)
    save_file_path = os.path.join(folder, semester_name + '.json')
    with open(save_file_path, 'w') as f:
        f.write(r.text)

    print('Download complete, importing ' + echo_text)
    subprocess.run(['python3', 'import_courses_new.py', save_file_path])
    print('Import ' + echo_text + ' complete')

